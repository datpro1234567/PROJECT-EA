import { handleSubmit, handleVerify, handleChangePassword } from "./api"

async function handleSignIn(e)
  {
    const result = await handleVerify({name,password})
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
      const result = await handleSubmit({name,password})
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
    const result = await handleVerify({name,password})
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
      const result = await handleChangePassword({id,password})
      if(result.status === "success")
      {
        handleMode(e)
      }
    }
    id.current=""
    setPassword("")
    setCPassword("")
  }