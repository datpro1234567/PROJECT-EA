import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";

export default function App({ initialMode = "signIn" }) {
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState("")
  const [fullName, setFullName] = useState("")
  const [password,setPassword] = useState("")
  const [cPassword,setCPassword] = useState("") // confirmation password
  const id = useRef("")
  const navigate = useNavigate()

  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

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
  function handleMode(e)
  {
    setMode(e.target.value)
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

  async function handleSignIn(e)
  {
    const result = await handleVertify()
    if (result.status === "success")
    {
      handleMode(e)
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
        setMode("signIn")
        navigate("/login")
      }
    }
    setPassword("")
    setCPassword("")
  }

  async function handleChangePassword(e)
  {
    const result = await handleVertify()
    if(result.status === "success")
    {
      handleMode(e)
      id.current=result.id
    }
    setName("")
    setPassword("")
  }

  async function handleChangePasswordPhase2(e)
  {
    if (password===cPassword)
    {
      const response = await fetch("http://localhost:5000/changePassword",
        {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({id: id.current, password_hash: password})
        }
      )
      const result = await response.json()
      if(result.status === "success")
      {
        setMode("signIn")
        navigate("/login")
      }
    }
    id.current=""
    setPassword("")
    setCPassword("")
  }

  let content;

  switch (mode) {
    case "home":
      content = (
        <div key="home">
          <button value="signIn" onClick={handleMode}>
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
          onChangeMode={handleMode}
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
          mode={mode}
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