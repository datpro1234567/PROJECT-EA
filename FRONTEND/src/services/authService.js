const BASE_URL = "http://localhost:5000"

export async function submitRegistration({ username, password, fullName }) {
  const response = await fetch(`${BASE_URL}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, full_name: fullName }),
  })
  return response.json()
}

export async function verifyUser({ username, password }) {
  const response = await fetch(`${BASE_URL}/vertify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  return response.json()
}

export async function changePassword({ id, password }) {
  const response = await fetch(`${BASE_URL}/changePassword`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, password }),
  })
  return response.json()
}
