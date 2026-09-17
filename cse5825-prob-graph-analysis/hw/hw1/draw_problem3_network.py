"""Draws the Problem 3(c) Bayesian network: A -> B, B -> C, B -> D."""
import networkx as nx
import matplotlib.pyplot as plt

G = nx.DiGraph()
G.add_edges_from([("A", "B"), ("B", "C"), ("B", "D")])

pos = {
    "A": (0, 0),
    "B": (1, 0),
    "C": (2, 0.6),
    "D": (2, -0.6),
}

fig, ax = plt.subplots(figsize=(4, 3))
nx.draw_networkx_nodes(G, pos, node_size=1400, node_color="#cfe2ff", edgecolors="black", ax=ax)
nx.draw_networkx_labels(G, pos, font_size=16, ax=ax)
nx.draw_networkx_edges(
    G, pos, ax=ax, arrowstyle="-|>", arrowsize=20, node_size=1400,
    connectionstyle="arc3,rad=0.0",
)

ax.set_axis_off()
fig.tight_layout()
fig.savefig("problem3_network.png", dpi=200, bbox_inches="tight")
print("saved problem3_network.png")
