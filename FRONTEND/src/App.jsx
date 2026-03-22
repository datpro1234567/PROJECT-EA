import {useState, usestate} from "react"
import "../src/App.css"

export default function App()
{
  const [name, setName] = useState("")
  const [email,setEmail] = useState("")

  function handleName(e)
  {
    setName(e.target.value)
  }
  function handlePassWord(e)
  {
    setName(e.target.value)
  }

  console.log(name, email)
  return(
    <div>
      <div id="body">
        <input placeholder="Enter your user name here: " onChange={handleName} id="inputName"></input>
        <input placeholder="Enter your password here: " onChange={handlePassWord} id="inputEmail"></input>
        <button id = "buttonSignIn">Sign in</button>
        <button id = "buttonSignUp">Sign up</button>
        <button id = "buttonForgotPassword">forgot password</button>
      </div>

      <div id="keyIcon">
        <div className="shaftKey"></div>
        <div className="headKey"></div>
        <div className="teethKey"></div>
      </div>
    </div>
  )
}