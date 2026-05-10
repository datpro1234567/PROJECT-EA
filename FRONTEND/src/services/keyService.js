const BASE_URL = "http://localhost:5000"

export async function generateKey({ userId }) {
  const response = await fetch(`${BASE_URL}/generate_key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  })
  return response.json()
}

export async function createRootCAKey() {
  const response = await fetch(`${BASE_URL}/create_root_ca_key`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  return response.json()
}
