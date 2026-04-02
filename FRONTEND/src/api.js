export async function submit({name, password})
  {
    const response = await fetch ("http://localhost:5000/submit",
      {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({name, password})
      }
    )
    const result = await response.json()
    return result
  }

  export async function verify({name, password})
  {
    const response = await fetch( "http://localhost:5000/verify",
      {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({name,password})
      }
    )
    const result = await response.json()
    return result
  }

  export async function changePassword({id, password})
  {
    const response = await fetch("http://localhost:5000/changePassword",
      {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({id: id.current, newPassword:password})// new password
      }
    )
    const result = await response.json()
    return result
  }