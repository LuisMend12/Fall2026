/* Study Ledger backend: owns all data storage and math.
 * Data lives in %APPDATA%\StudyLedger as two flat pipe-delimited files:
 *   sessions.dat -> id|date|minutes|subject|note
 *   todos.dat    -> id|done|text
 * Exposed as a DLL; the Python frontend talks to it through ctypes. */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <direct.h>

#define MAX_LINE 512

static void get_data_dir(char *out, size_t outsz) {
    const char *appdata = getenv("APPDATA");
    if (!appdata) appdata = ".";
    snprintf(out, outsz, "%s\\StudyLedger", appdata);
}

static void get_path(char *out, size_t outsz, const char *filename) {
    char dir[512];
    get_data_dir(dir, sizeof(dir));
    _mkdir(dir);
    snprintf(out, outsz, "%s\\%s", dir, filename);
}

static void sanitize(char *s) {
    for (; *s; s++) {
        if (*s == '|' || *s == '\n' || *s == '\r') *s = ' ';
    }
}

static int next_id_from_file(const char *path) {
    FILE *f = fopen(path, "r");
    int maxid = 0;
    if (!f) return 1;
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), f)) {
        int id = atoi(line);
        if (id > maxid) maxid = id;
    }
    fclose(f);
    return maxid + 1;
}

/* Splits "id|done|text" (or any 3-field pipe line) without disturbing
 * the raw line buffer's caller-owned memory. */
static int parse3(const char *line, int *a, int *b, char *rest, size_t restsz) {
    const char *p1 = strchr(line, '|');
    if (!p1) return -1;
    const char *p2 = strchr(p1 + 1, '|');
    if (!p2) return -1;
    char buf1[32], buf2[32];
    size_t l1 = (size_t)(p1 - line);
    if (l1 >= sizeof(buf1)) l1 = sizeof(buf1) - 1;
    memcpy(buf1, line, l1); buf1[l1] = 0;
    size_t l2 = (size_t)(p2 - (p1 + 1));
    if (l2 >= sizeof(buf2)) l2 = sizeof(buf2) - 1;
    memcpy(buf2, p1 + 1, l2); buf2[l2] = 0;
    *a = atoi(buf1);
    *b = atoi(buf2);
    size_t tlen = strlen(p2 + 1);
    while (tlen > 0 && (p2[1 + tlen - 1] == '\n' || p2[1 + tlen - 1] == '\r')) tlen--;
    if (tlen >= restsz) tlen = restsz - 1;
    memcpy(rest, p2 + 1, tlen);
    rest[tlen] = 0;
    return 0;
}

__declspec(dllexport)
int sl_add_session(const char *subject, double minutes, const char *date, const char *note) {
    char path[512];
    get_path(path, sizeof(path), "sessions.dat");
    int id = next_id_from_file(path);
    FILE *f = fopen(path, "a");
    if (!f) return -1;
    char subj[128], nt[256], dt[32];
    snprintf(subj, sizeof(subj), "%s", subject ? subject : "");
    snprintf(nt, sizeof(nt), "%s", note ? note : "");
    snprintf(dt, sizeof(dt), "%s", date ? date : "");
    sanitize(subj); sanitize(nt); sanitize(dt);
    fprintf(f, "%d|%s|%.2f|%s|%s\n", id, dt, minutes, subj, nt);
    fclose(f);
    return id;
}

__declspec(dllexport)
int sl_delete_session(int id) {
    char path[512];
    get_path(path, sizeof(path), "sessions.dat");
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char tmp[520];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *out = fopen(tmp, "w");
    if (!out) { fclose(f); return -1; }
    char line[MAX_LINE];
    int found = 0;
    while (fgets(line, sizeof(line), f)) {
        int lid = atoi(line);
        if (lid == id) { found = 1; continue; }
        fputs(line, out);
    }
    fclose(f); fclose(out);
    remove(path);
    rename(tmp, path);
    return found ? 0 : -1;
}

/* Inclusive sum over ISO date strings; works because YYYY-MM-DD sorts
 * lexicographically. Pass "0000-01-01".."9999-12-31" for an all-time sum. */
__declspec(dllexport)
int sl_sum_range(const char *start_date, const char *end_date, double *out_minutes) {
    char path[512];
    get_path(path, sizeof(path), "sessions.dat");
    *out_minutes = 0.0;
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), f)) {
        char copy[MAX_LINE];
        snprintf(copy, sizeof(copy), "%s", line);
        char *idtok = strtok(copy, "|");
        char *datetok = strtok(NULL, "|");
        char *mintok = strtok(NULL, "|");
        if (!idtok || !datetok || !mintok) continue;
        if (strcmp(datetok, start_date) >= 0 && strcmp(datetok, end_date) <= 0) {
            *out_minutes += atof(mintok);
        }
    }
    fclose(f);
    return 0;
}

/* Dumps the raw file into buffer (id|date|minutes|subject|note per line).
 * Returns 0 if it fit, 1 if truncated. Frontend parses/groups it. */
__declspec(dllexport)
int sl_get_history(char *buffer, int buffer_size) {
    char path[512];
    get_path(path, sizeof(path), "sessions.dat");
    buffer[0] = '\0';
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    int len = 0, truncated = 0;
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), f)) {
        int l = (int)strlen(line);
        if (len + l >= buffer_size - 1) { truncated = 1; break; }
        memcpy(buffer + len, line, l);
        len += l;
    }
    buffer[len] = '\0';
    fclose(f);
    return truncated;
}

__declspec(dllexport)
int sl_add_todo(const char *text) {
    char path[512];
    get_path(path, sizeof(path), "todos.dat");
    int id = next_id_from_file(path);
    FILE *f = fopen(path, "a");
    if (!f) return -1;
    char t[256];
    snprintf(t, sizeof(t), "%s", text ? text : "");
    sanitize(t);
    fprintf(f, "%d|0|%s\n", id, t);
    fclose(f);
    return id;
}

__declspec(dllexport)
int sl_set_todo_done(int id, int done) {
    char path[512];
    get_path(path, sizeof(path), "todos.dat");
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char tmp[520];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *out = fopen(tmp, "w");
    if (!out) { fclose(f); return -1; }
    char line[MAX_LINE];
    int found = 0;
    while (fgets(line, sizeof(line), f)) {
        int lid = 0, ldone = 0;
        char text[256];
        if (parse3(line, &lid, &ldone, text, sizeof(text)) == 0) {
            if (lid == id) { ldone = done ? 1 : 0; found = 1; }
            fprintf(out, "%d|%d|%s\n", lid, ldone, text);
        } else {
            fputs(line, out);
        }
    }
    fclose(f); fclose(out);
    remove(path);
    rename(tmp, path);
    return found ? 0 : -1;
}

__declspec(dllexport)
int sl_delete_todo(int id) {
    char path[512];
    get_path(path, sizeof(path), "todos.dat");
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char tmp[520];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *out = fopen(tmp, "w");
    if (!out) { fclose(f); return -1; }
    char line[MAX_LINE];
    int found = 0;
    while (fgets(line, sizeof(line), f)) {
        int lid = atoi(line);
        if (lid == id) { found = 1; continue; }
        fputs(line, out);
    }
    fclose(f); fclose(out);
    remove(path);
    rename(tmp, path);
    return found ? 0 : -1;
}

__declspec(dllexport)
int sl_get_todos(char *buffer, int buffer_size) {
    char path[512];
    get_path(path, sizeof(path), "todos.dat");
    buffer[0] = '\0';
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    int len = 0, truncated = 0;
    char line[MAX_LINE];
    while (fgets(line, sizeof(line), f)) {
        int l = (int)strlen(line);
        if (len + l >= buffer_size - 1) { truncated = 1; break; }
        memcpy(buffer + len, line, l);
        len += l;
    }
    buffer[len] = '\0';
    fclose(f);
    return truncated;
}
