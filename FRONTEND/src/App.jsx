import {useState, useRef} from "react"
import "../src/App.css"
import SignIn from "./components/SignIn"
import SignUp from "./components/SignUp"
import ChangePasswordPhase1 from "./components/ChangePasswordPhase1"
import ChangePasswordPhase2 from "./components/ChangePasswordPhase2"
import { submit, verify, changePassword } from "./api"

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

  async function handleSignIn(e)
  {
    const result = await verify({name,password})
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
      const result = await submit({name,password})
      if (result.status === "success")
      {
        handleMode(e)
        setName("")
      }
    }
    setPassword("")
    setCPassword("")
  }

  async function handleChangePasswordPhase1(e)
  {
    const result = await verify({name,password})
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
      const result = await changePassword({id,password})
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
    case "home"://////////////////////////////////////////////////////
      content =
      <div key="home">
        <button value="signIn" onClick={handleMode}>Sign out</button>
      </div>
      break;//////////////////////////////////////////////////////
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

    case "ChangePasswordPhase1":
      content = <ChangePasswordPhase1 name = {name} handleName = {handleName} password = {password}
                 handlePassword = {handlePassword} handleChangePasswordPhase1 ={handleChangePasswordPhase1}></ChangePasswordPhase1>      
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