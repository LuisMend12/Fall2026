"""Baseline results for Project 0: "Which edges can a GNN trust?"

Dataset: WikiCS (11,701 Wikipedia CS articles, 10 classes), loaded from the
original JSON release (github.com/pmernyei/wiki-cs-dataset).

Attack: inject fake edges between nodes whose texts look related (top-K SBERT
neighbours) but that carry different labels, at 5-40% of the clean edge count.
A uniformly random injection at 20% is included for contrast.

Baselines
  Node classification : MLP (no graph), GCN on clean / attacked / oracle-cleaned graph.
                        Accuracy, NLL, ECE, Brier on the test set.
  Fake-edge detection : text-only (SBERT, GloVe cosine), structure-only (neighbourhood
                        Jaccard, GCN prediction disagreement), and a naive unweighted
                        rank-average of text + structure. AUROC / AUPRC, fake = positive.

Usage:  python baselines/run_baselines.py [--splits 3] [--epochs 300]
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from scipy.stats import rankdata
from sklearn.metrics import average_precision_score, roc_auc_score
from torch_geometric.nn import GCNConv
from torch_geometric.utils import to_undirected

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "wikics"
OUT = ROOT / "baselines" / "results"


# ----------------------------------------------------------------------------- data
def load_wikics():
    d = json.loads((DATA / "data.json").read_text())
    meta = json.loads((DATA / "metadata.json").read_text(encoding="utf8"))
    x = torch.tensor(d["features"], dtype=torch.float)
    y = torch.tensor(d["labels"], dtype=torch.long)
    src = [i for i, nb in enumerate(d["links"]) for _ in nb]
    dst = [j for nb in d["links"] for j in nb]
    ei = torch.tensor([src, dst], dtype=torch.long)
    ei = ei[:, ei[0] != ei[1]]
    ei = to_undirected(ei)
    und = ei[:, ei[0] < ei[1]]  # unique undirected pairs
    texts = [n["title"] + ". " + " ".join(n["tokens"][:256]) for n in meta["nodes"]]
    masks = {
        "train": torch.tensor(d["train_masks"], dtype=torch.bool),
        "val": torch.tensor(d["val_masks"], dtype=torch.bool),
        "test": torch.tensor(d["test_mask"], dtype=torch.bool),
    }
    return x, y, und, texts, masks


def sbert_embeddings(texts):
    cache = DATA / "sbert_minilm.npy"
    if cache.exists():
        return np.load(cache)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    emb = model.encode(texts, batch_size=128, show_progress_bar=True, normalize_embeddings=True)
    np.save(cache, emb.astype(np.float32))
    return emb


# --------------------------------------------------------------------------- attack
def text_similar_candidates(emb, y, existing, k=60):
    """Non-adjacent, different-label pairs among each node's top-k SBERT neighbours."""
    e = torch.from_numpy(emb)
    n = e.shape[0]
    cands = set()
    for s in range(0, n, 2048):
        sim = e[s : s + 2048] @ e.T
        sim[torch.arange(sim.shape[0]), torch.arange(s, s + sim.shape[0])] = -1
        top = sim.topk(k, dim=1).indices.numpy()
        for r, row in enumerate(top):
            u = s + r
            for v in row:
                a, b = (u, int(v)) if u < v else (int(v), u)
                if (a, b) not in existing and y[a] != y[b]:
                    cands.add((a, b))
    return np.array(sorted(cands))


def inject(und, n_nodes, budget, mode, cands, y, rng, existing):
    m = und.shape[1]
    n_fake = int(round(budget * m))
    if n_fake == 0:
        fake = np.zeros((0, 2), dtype=np.int64)
    elif mode == "text":
        fake = cands[rng.choice(len(cands), size=n_fake, replace=False)]
    else:  # uniformly random non-edges (any labels)
        picked = set()
        while len(picked) < n_fake:
            a, b = rng.integers(0, n_nodes, size=2)
            a, b = (int(a), int(b)) if a < b else (int(b), int(a))
            if a != b and (a, b) not in existing:
                picked.add((a, b))
        fake = np.array(sorted(picked))
    all_pairs = np.concatenate([und.numpy().T, fake]) if len(fake) else und.numpy().T
    is_fake = np.r_[np.zeros(m, bool), np.ones(len(fake), bool)]
    return all_pairs, is_fake


def to_ei(pairs):
    return to_undirected(torch.as_tensor(pairs.T, dtype=torch.long))


# --------------------------------------------------------------------------- models
class MLP(torch.nn.Module):
    def __init__(self, d, h, c):
        super().__init__()
        self.l1, self.l2 = torch.nn.Linear(d, h), torch.nn.Linear(h, c)

    def forward(self, x, ei=None):
        return self.l2(F.dropout(F.relu(self.l1(F.dropout(x, 0.5, self.training))), 0.5, self.training))


class GCN(torch.nn.Module):
    def __init__(self, d, h, c):
        super().__init__()
        self.c1, self.c2 = GCNConv(d, h, cached=True), GCNConv(h, c, cached=True)

    def forward(self, x, ei):
        x = F.dropout(x, 0.5, self.training)
        x = F.relu(self.c1(x, ei))
        return self.c2(F.dropout(x, 0.5, self.training), ei)


def train_model(cls, x, y, ei, tr, va, epochs, seed):
    torch.manual_seed(seed)
    model = cls(x.shape[1], 64, int(y.max()) + 1)
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    best, best_state, patience = float("inf"), None, 0
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        F.cross_entropy(model(x, ei)[tr], y[tr]).backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            vl = F.cross_entropy(model(x, ei)[va], y[va]).item()
        if vl < best:
            best, best_state, patience = vl, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 50:
                break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        return F.softmax(model(x, ei), dim=1)


# -------------------------------------------------------------------------- metrics
def ece(p, y, bins=15):
    conf, pred = p.max(1)
    acc = (pred == y).float()
    edges = torch.linspace(0, 1, bins + 1)
    out = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            out += m.float().mean().item() * abs(acc[m].mean().item() - conf[m].mean().item())
    return out


def node_metrics(p, y, mask):
    p, y = p[mask], y[mask]
    onehot = F.one_hot(y, p.shape[1]).float()
    return {
        "acc": (p.argmax(1) == y).float().mean().item(),
        "nll": F.nll_loss(torch.log(p.clamp_min(1e-12)), y).item(),
        "ece": ece(p, y),
        "brier": ((p - onehot) ** 2).sum(1).mean().item(),
    }


def jaccard_scores(pairs, n):
    nbrs = [set() for _ in range(n)]
    for a, b in pairs:
        nbrs[a].add(b)
        nbrs[b].add(a)
    out = np.empty(len(pairs))
    for i, (a, b) in enumerate(pairs):
        na, nb = nbrs[a] - {b}, nbrs[b] - {a}
        u = len(na | nb)
        out[i] = len(na & nb) / u if u else 0.0
    return out


def js_div(p, q):
    m = 0.5 * (p + q)
    kl = lambda a, b: (a * (np.log(a + 1e-12) - np.log(b + 1e-12))).sum(1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def detection(pairs, is_fake, scores):
    res = {}
    for name, s in scores.items():
        res[name] = {"auroc": roc_auc_score(is_fake, s), "auprc": average_precision_score(is_fake, s)}
    return res


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--budgets", type=float, nargs="+", default=[0.0, 0.05, 0.10, 0.20, 0.40])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    x, y, und, texts, masks = load_wikics()
    n = x.shape[0]
    print(f"WikiCS: {n} nodes, {und.shape[1]} undirected edges, {int(y.max()) + 1} classes")
    homophily = (y[und[0]] == y[und[1]]).float().mean().item()
    print(f"edge homophily (clean): {homophily:.3f}")

    emb = sbert_embeddings(texts)
    xg = F.normalize(x, dim=1).numpy()
    existing = set(map(tuple, und.numpy().T.tolist()))
    cands = text_similar_candidates(emb, y.numpy(), existing)
    print(f"text-similar cross-label candidate pairs: {len(cands)}")
    need = int(round(max(args.budgets) * und.shape[1]))
    if need > len(cands):
        raise SystemExit(f"budget {max(args.budgets):.0%} needs {need} fake edges but only {len(cands)} candidates; raise k")

    settings = [("text", b) for b in args.budgets] + [("random", 0.20)]
    rows = []
    for mode, b in settings:
        for split in range(args.splits):
            rng = np.random.default_rng(1000 + split)
            pairs, is_fake = inject(und, n, b, mode, cands, y.numpy(), rng, existing)
            ei = to_ei(pairs)
            tr, va, te = masks["train"][split], masks["val"][split], masks["test"]
            touched = torch.zeros(n, dtype=torch.bool)
            if is_fake.any():
                touched[torch.as_tensor(pairs[is_fake].ravel())] = True

            row = {"mode": mode, "budget": b, "split": split, "n_fake": int(is_fake.sum())}
            p_gcn = train_model(GCN, x, y, ei, tr, va, args.epochs, split)
            row["gcn"] = node_metrics(p_gcn, y, te)
            row["gcn_touched_acc"] = node_metrics(p_gcn, y, te & touched)["acc"] if (te & touched).any() else None
            row["gcn_untouched_acc"] = node_metrics(p_gcn, y, te & ~touched)["acc"]
            if b == 0.0 and mode == "text":
                p_mlp = train_model(MLP, x, y, ei, tr, va, args.epochs, split)
                row["mlp"] = node_metrics(p_mlp, y, te)

            if is_fake.any():
                # oracle: train on the clean graph (fakes removed) = upper bound for any defense
                a, c = pairs[:, 0], pairs[:, 1]
                pg = p_gcn.numpy()
                s_text = 1 - (emb[a] * emb[c]).sum(1)
                s_glove = 1 - (xg[a] * xg[c]).sum(1)
                s_jac = 1 - jaccard_scores(pairs, n)
                s_gcn = js_div(pg[a], pg[c])
                rk = lambda s: rankdata(s) / len(s)
                scores = {
                    "text_sbert": s_text,
                    "text_glove": s_glove,
                    "struct_jaccard": s_jac,
                    "struct_gcn_disagree": s_gcn,
                    "naive_mix(sbert+gcn)": 0.5 * (rk(s_text) + rk(s_gcn)),
                    "naive_mix(sbert+jaccard)": 0.5 * (rk(s_text) + rk(s_jac)),
                }
                row["detect"] = detection(pairs, is_fake, scores)
            rows.append(row)
            (OUT / "raw.json").write_text(json.dumps(rows, indent=1))
            print(f"[{time.time() - t0:6.0f}s] {mode:6s} b={b:.2f} split={split} "
                  f"gcn acc={row['gcn']['acc']:.3f} ece={row['gcn']['ece']:.3f}"
                  + (f"  mlp acc={row['mlp']['acc']:.3f}" if "mlp" in row else ""))

    (OUT / "raw.json").write_text(json.dumps(rows, indent=1))
    write_summary(rows, homophily, len(cands), und.shape[1])
    print(f"done in {time.time() - t0:.0f}s -> {OUT}")


def ms(vals):
    v = np.array([x for x in vals if x is not None])
    return f"{v.mean():.3f} ± {v.std():.3f}" if len(v) else "—"


def write_summary(rows, homophily, n_cands, m):
    L = ["# Baseline results — WikiCS", "",
         f"- {m} clean undirected edges, edge homophily {homophily:.3f}",
         f"- {n_cands} text-similar, cross-label candidate pairs (top-60 SBERT neighbours)",
         f"- mean ± std over {len({r['split'] for r in rows})} splits; GCN = 2-layer, 64 hidden, GloVe features", ""]
    L += ["## Node classification (test set)", "",
          "| model | attack | budget | acc | NLL | ECE | Brier | acc (touched) | acc (untouched) |",
          "|---|---|---|---|---|---|---|---|---|"]
    clean = [r for r in rows if r["budget"] == 0.0 and "mlp" in r]
    L.append(f"| MLP (no graph) | — | — | {ms(r['mlp']['acc'] for r in clean)} | {ms(r['mlp']['nll'] for r in clean)} "
             f"| {ms(r['mlp']['ece'] for r in clean)} | {ms(r['mlp']['brier'] for r in clean)} | — | — |")
    keys = sorted({(r["mode"], r["budget"]) for r in rows}, key=lambda k: (k[0] != "text", k[1]))
    for mode, b in keys:
        g = [r for r in rows if r["mode"] == mode and r["budget"] == b]
        L.append(f"| GCN | {mode if b else 'none'} | {b:.0%} | {ms(r['gcn']['acc'] for r in g)} | {ms(r['gcn']['nll'] for r in g)} "
                 f"| {ms(r['gcn']['ece'] for r in g)} | {ms(r['gcn']['brier'] for r in g)} "
                 f"| {ms(r['gcn_touched_acc'] for r in g)} | {ms(r['gcn_untouched_acc'] for r in g)} |")
    L += ["", "GCN at budget 0% is also the oracle defense (all fake edges removed) for every attacked row.", ""]
    L += ["## Fake-edge detection (AUROC / AUPRC, fake = positive)", ""]
    det = [r for r in rows if "detect" in r]
    names = list(det[0]["detect"].keys())
    L += ["| attack | budget | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for mode, b in keys:
        g = [r for r in det if r["mode"] == mode and r["budget"] == b]
        if not g:
            continue
        cells = [f"{np.mean([r['detect'][k]['auroc'] for r in g]):.3f} / {np.mean([r['detect'][k]['auprc'] for r in g]):.3f}"
                 for k in names]
        L.append(f"| {mode} | {b:.0%} | " + " | ".join(cells) + " |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n", encoding="utf8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
