import {useState} from "react"
import "../src/App.css"

export default function App()
{
  const[mode,setMode] = useState("signIn")
  const [name, setName] = useState("")
  const [password,setPassword] = useState("")

  function handleName(e)
  {
    setName(e.target.value)
  }
  function handlePassWord(e)
  {
    setPassword(e.target.value)
  }
  function handleMode(e)
  {
    setMode(e.target.value)
  }

  let content

  switch (mode) {
    case "signIn":
      content =
      <div id="signIn">
        <div>
          <input placeholder="Enter your user name here: " onChange={handleName} id="inputName"></input>
          <input placeholder="Enter your password here: " onChange={handlePassWord} id="inputEmail"></input>
          <button id = "buttonSignIn">Sign in</button>
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
    <div id = "signUp">
      <input placeholder="Create your user name: "></input>
      <input placeholder="Create your password: "></input>
      <input placeholder="Confirm your password: "></input>
      <button value="signIn" onClick={handleMode}>Create</button>
    </div>
      break;

    case "changePassword":
      content = 
      <div id="changePassword">
        <input placeholder="Enter your password: "></input>
        <input placeholder="Create your new password: "></input>
        <input placeholder="Confirm your new password"></input>
        <button value = "signIn" onClick={handleMode}>Confirm</button>
      </div>
      break;

    default:
      break;
  }

  console.log(name, password)
  
  return content
}

// rename forgot password to change password