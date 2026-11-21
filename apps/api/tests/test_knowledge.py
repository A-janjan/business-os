"""Knowledge layer: vault CRUD, frontmatter, search, traversal protection."""


def test_structure(client_and_token):
    c, headers = client_and_token
    r = c.get("/api/knowledge/structure", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "folders" in body and "notes_total" in body


def test_create_and_read_note(client_and_token, vault_dir):
    c, headers = client_and_token
    r = c.post("/api/knowledge/notes", headers=headers, json={
        "path": "01-CLIENTS/Test-Client.md",
        "frontmatter": {"title": "Test Client", "type": "client", "tags": ["test"]},
        "body": "# Test Client\n\nA client note.",
    })
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["path"] == "01-CLIENTS/Test-Client.md"
    assert note["title"] == "Test Client"

    r = c.get("/api/knowledge/note?path=01-CLIENTS/Test-Client.md", headers=headers)
    assert r.status_code == 200
    assert r.json()["body"].startswith("# Test Client")


def test_duplicate_note_rejected(client_and_token):
    c, headers = client_and_token
    c.post("/api/knowledge/notes", headers=headers, json={
        "path": "06-RESEARCH/dupe.md", "frontmatter": {"title": "D"}, "body": "",
    })
    r = c.post("/api/knowledge/notes", headers=headers, json={
        "path": "06-RESEARCH/dupe.md", "frontmatter": {"title": "D"}, "body": "",
    })
    assert r.status_code == 404  # KnowledgeError mapped to 404


def test_path_traversal_blocked(client_and_token):
    c, headers = client_and_token
    r = c.post("/api/knowledge/notes", headers=headers, json={
        "path": "../../escape.md", "frontmatter": {"title": "x"}, "body": "",
    })
    assert r.status_code in (400, 404, 422)


def test_note_update_and_search(client_and_token):
    c, headers = client_and_token
    c.post("/api/knowledge/notes", headers=headers, json={
        "path": "04-CONTENT/Searchable.md", "frontmatter": {"title": "Searchable Note", "tags": ["marker"]},
        "body": "Some searchable body text.",
    })
    r = c.patch("/api/knowledge/note", headers=headers, json={
        "path": "04-CONTENT/Searchable.md", "body": "Updated searchable body.",
    })
    assert r.status_code == 200
    assert "Updated searchable body" in r.json()["body"]

    r = c.get("/api/knowledge/notes?q=searchable", headers=headers)
    assert r.status_code == 200
    assert any("Searchable" in n["title"] for n in r.json()["items"])


def test_archive_moved_to_archive(client_and_token):
    c, headers = client_and_token
    c.post("/api/knowledge/notes", headers=headers, json={
        "path": "07-DAILY-NOTES/to-archive.md", "frontmatter": {"title": "Archive Me"}, "body": "x",
    })
    r = c.post("/api/knowledge/note/archive", headers=headers, json={"path": "07-DAILY-NOTES/to-archive.md"})
    assert r.status_code == 200
    assert "10-ARCHIVE/" in r.json()["archived_to"]


def test_backlinks_detect_wiki_links(client_and_token):
    c, headers = client_and_token
    c.post("/api/knowledge/notes", headers=headers, json={
        "path": "01-CLIENTS/Linked-Client.md", "frontmatter": {"title": "Linked Client"}, "body": "# Linked\n\nSome note.",
    })
    c.post("/api/knowledge/notes", headers=headers, json={
        "path": "06-RESEARCH/Linking.md", "frontmatter": {"title": "Linker"},
        "body": "See [[Linked-Client]] for context.",
    })
    r = c.get("/api/knowledge/backlinks?path=01-CLIENTS/Linked-Client.md", headers=headers)
    assert r.status_code == 200
    assert any("Linking.md" in p for p in r.json()["backlinks"])
