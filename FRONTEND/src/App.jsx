import {useState, useRef} from "react"
import "../src/App.css"

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
      content =
      <div id="signIn" key='signIn'>
        <div>
          <input value={name} placeholder="Enter your user name here: " onChange={handleName} id="inputName"></input>
          <input value={password} placeholder="Enter your password here: " onChange={handlePassword} id="inputEmail"></input>
          <button value="home" id = "buttonSignIn" onClick={(e) => handleSignIn(e)}>Sign in</button>
          <button value="signUp" id = "buttonSignUp" onClick={handleMode}>Sign up</button>
          <button value = "changePassword" id = "buttonChangePassword" onClick={handleMode}>change password</button>
        </div>
        <div id="keyIcon">
            <div className="shaftKey"></div>
            <div className="headKey"></div>
            <div className="teethKey"></div>
        </div>
      </div>
      break;

    case "signUp":
    content = 
    <div id = "signUp" key="signUp">
      <input value = {name} placeholder="Create your user name: " onChange={handleName}></input>
      <input value = {password} placeholder="Create your password: " onChange={handlePassword}></input>
      <input value = {cPassword} placeholder="Confirm your password: " onChange={handleCPassword}></input>
      <button value="signIn" onClick={(e) => 
        {handleSignUp(e)}}>
        Create
      </button> 
    </div>
      break;

    case "changePassword":
      content = 
      <div id="changePassword" key="changePassword" >
        <input value={name} placeholder="Enter your userName: " onChange={handleName}></input>
        <input value={password} placeholder="Enter your password: " onChange={handlePassword}></input>
        <button value ="changePasswordPhase2" onClick={handleChangePassword}>Confirm</button>
      </div>  
      
      break;

    case "changePasswordPhase2":
      content =
      <div key="changePasswordPhase2">
        <input value = {password} placeholder="Create your new password: " onChange ={handlePassword}></input>
        <input value = {cPassword} placeholder="Confirm your new password: "onChange={handleCPassword}></input>
        <button value = "signIn" onClick={handleChangePasswordPhase2}>Confirm</button>
      </div>
      break;

    default:
      break;
  }
  
  return content
}

// create handle vertify