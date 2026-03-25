import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";

export default function App({ initialMode = "signIn" }) {
  const [name, setName] = useState("")
  const [fullName, setFullName] = useState("")
  const [password,setPassword] = useState("")
  const [cPassword,setCPassword] = useState("") // confirmation password
  const navigate = useNavigate()
  const { id } = useParams()

  function handleName(e)
  {
    setName(e.target.value)
  }
  function handleFullName(e)
  {
    setFullName(e.target.value)
  }
  function handlePassword(e)
  {
    setPassword(e.target.value)
  }
  function handleCPassword(e)
  {
    setCPassword(e.target.value)
  }

  async function handleSubmit()
  {
    const response = await fetch ("http://localhost:5000/submit",
      {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({username: name, password_hash: password})
      }
    )
    const result = await response.json()
    return result
  }

  async function handleVertify(e)
  {
    const response = await fetch( "http://localhost:5000/vertify",
      {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({username: name, password_hash: password})
      }
    )
    const result = await response.json()
    return result
  }

  async function handleSignIn()
  {
    const result = await handleVertify()
    if (result.status === "success")
    {
      if (result.full_name) {
        setFullName(result.full_name)
      } else {
        setFullName(name)
      }
      navigate("/home")
    }
    setName("")
    setPassword("")
  }

  async function handleSignUp(e)
  {
    if (password === cPassword)
    {
      const result = await handleSubmit()
      if (result.status === "success")
      {
        setName("")
        setFullName("")
        navigate("/login")
      }
    }
    setPassword("")
    setCPassword("")
  }

  async function handleChangePassword()
  {
    const result = await handleVertify()
    if(result.status === "success")
    {
      const userId = result.id
      navigate(`/change-password/${userId}`)
    }
    setName("")
    setPassword("")
  }

  async function handleChangePasswordPhase2()
  {
    if (password===cPassword)
    {
      const response = await fetch("http://localhost:5000/changePassword",
        {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({id, password_hash: password})
        }
      )
      const result = await response.json()
      if(result.status === "success")
      {
        navigate("/login")
      }
    }
    setPassword("")
    setCPassword("")
  }

  function handleSignOut() {
    navigate("/login")
  }

  let content;

  switch (initialMode) {
    case "home":
      content = (
        <div key="home">
          <p>Hello {fullName}</p>
          <button onClick={handleSignOut}> 
            Sign out
          </button>
        </div>
      );
      break;
    case "signIn":
      content = (
        <Login
          name={name}
          password={password}
          onNameChange={handleName}
          onPasswordChange={handlePassword}
          onSignIn={handleSignIn}
        />
      );
      break;
    case "signUp":
      content = (
        <Register
          name={name}
          fullName={fullName}
          password={password}
          cPassword={cPassword}
          onNameChange={handleName}
          onFullNameChange={handleFullName}
          onPasswordChange={handlePassword}
          onCPasswordChange={handleCPassword}
          onSignUp={handleSignUp}
        />
      );
      break;
    case "changePassword":
    case "changePasswordPhase2":
      content = (
        <ForgotPassword
          mode={initialMode}
          name={name}
          password={password}
          cPassword={cPassword}
          onNameChange={handleName}
          onPasswordChange={handlePassword}
          onCPasswordChange={handleCPassword}
          onChangePassword={handleChangePassword}
          onChangePasswordPhase2={handleChangePasswordPhase2}
        />
      );
      break;
    default:
      content = null;
      break;
  }

  return content;
}

// create handle vertify