import {useState, useRef} from "react"
import "../src/App.css"
import SignIn from "./components/SignIn"
import SignUp from "./components/SignUp"
import ChangePassword from "./components/ChangePassword"
import ChangePasswordPhase2 from "./components/ChangePasswordPhase2"

export default function App()
{
  const[mode,setMode] = useState("signIn")
  const [name, setName] = useState("")
  const [password,setPassword] = useState("")
  const [cPassword,setCPassword] = useState("") // confirmation password
  const id = useRef("")

  function handleName(e)
  {
    setName(e.target.value)
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
        body: JSON.stringify({name, password})
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
        body: JSON.stringify({name,password})
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
        handleMode(e)
        setName("")
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
          body: JSON.stringify({id: id.current, password:password})
        }
      )
      const result = await response.json()
      if(result.status === "success")
      {
        handleMode(e)
      }
    }
    id.current=""
    setPassword("")
    setCPassword("")
  }

  let content

  switch (mode) {
    case "home":
      content =
      <div key="home">
        <button value="signIn" onClick={handleMode}>Sign out</button>
      </div>
      break;
    case "signIn":
      content = <SignIn name = {name} handleName = {handleName} password = {password}
                handlePassword = {handlePassword} handleSignIn = {handleSignIn}
                handleMode  = {handleMode}></SignIn>
      break;

    case "signUp":
      content = <SignUp name = {name} handleName = {handleName} password = {password}
                handlePassword = {handlePassword} cPassword = {cPassword}
                handleCPassword = {handleCPassword} handleSignUp = {handleSignUp}></SignUp>
      break;

    case "changePassword":
      content = <ChangePassword name = {name} handleName = {handleName} password = {password}
                 handlePassword = {handlePassword} handleChangePassword ={handleChangePassword}></ChangePassword>      
      break;

    case "changePasswordPhase2":
      content = <ChangePasswordPhase2 password = {password} handlePassword = {handlePassword}
                 cPassword = {cPassword} handleCPassword = {handleCPassword}
                 handleChangePasswordPhase2 = {handleChangePasswordPhase2}></ChangePasswordPhase2>
      break;

    default:
      break;
  }
  
  return content
}

// create handle vertify