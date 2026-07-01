// The browser talks to the API via the published port on the host. NEXT_PUBLIC_*
// vars are inlined at build time; the default works for the docker-compose setup.
const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function search(query, mode, k = 5) {
  const res = await fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mode, k }),
  });
  if (!res.ok) throw new Error(`search failed (${res.status})`);
  return res.json();
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`upload failed (${res.status})`);
  return res.json();
}

export async function getDocument(id) {
  const res = await fetch(`${BASE}/documents/${id}`);
  if (!res.ok) throw new Error(`status check failed (${res.status})`);
  return res.json();
}
