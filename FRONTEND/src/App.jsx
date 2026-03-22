import {useState, usestate} from "react"

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
      <input placeholder="Enter your user name here: " onChange={handleName}></input>
      <input placeholder="Enter your password here: " onChange={handlePassWord}></input>
      <button>Sign in</button>
      <button>Sign up</button>
      <button>forgot password</button>
    </div>
  )
}