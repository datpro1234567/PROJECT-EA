import { useState, useEffect } from "react";
import { useNavigate, useParams, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";

export default function App({ initialMode = "signIn" }) {
  const [name, setName] = useState("")
  const [fullName, setFullName] = useState("")
  const [password,setPassword] = useState("")
  const [cPassword,setCPassword] = useState("") // confirmation password
  const [userId, setUserId] = useState(null)
  const [role, setRole] = useState(null)
  const navigate = useNavigate()
  const { id } = useParams()

  // Load user info from localStorage on app initialization (?)
  useEffect(() => {
    const stored = localStorage.getItem("userInfo")
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        if (parsed.id) {
          setUserId(parsed.id)
        }
        if (parsed.fullName) {
          setFullName(parsed.fullName)
        }
        if (parsed.role) {
          setRole(parsed.role)
        }
      } catch {
        // ignore parse errors
      }
    }
  }, [])

  // Khi vào trang đăng ký, luôn reset form để không prefill dữ liệu admin
  useEffect(() => {
    if (initialMode === "signUp") {
      setName("")
      setFullName("")
      setPassword("")
      setCPassword("")
    }
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
        body: JSON.stringify({username: name, password_hash: password, full_name: fullName})
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
      if (result.id) {
        setUserId(result.id)
      }
      if (result.full_name) {
        setFullName(result.full_name)
      } else {
        setFullName(name)
      }
      if (result.role) {
        setRole(result.role)
      }

      const userInfo = {
        id: result.id,
        fullName: result.full_name || name,
        role: result.role || "user",
      }
      localStorage.setItem("userInfo", JSON.stringify(userInfo))

      if (result.role === "admin") {
        navigate("/admin_home")
      } else {
        navigate("/home")
      }
    }
    setName("")
    setPassword("")
  }

  async function handleSignUp(e)
  {
    if (!fullName || !name || !password || !cPassword) {
      alert("Please fill in all fields");
      return;
    }
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
    setName("")
    setFullName("")
    setPassword("")
    setCPassword("")
    setUserId(null)
    setRole(null)
    localStorage.removeItem("userInfo")
    navigate("/login")
  }

  function goToChangePassword() {
    setName("")
    setPassword("")
    navigate("/change-password")
  }

  async function handleGenerateKey() {
    if (!userId) {
      alert("User not found. Please login again.");
      return;
    }

    const response = await fetch("http://localhost:5000/generate_key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });

    const result = await response.json();
    if (result.status !== "success") {
      alert(result.message || "Failed to generate key");
      return;
    }

    const privateKeyPem = result.private_key_pem;
    const blob = new Blob([privateKeyPem], { type: "application/x-pem-file" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "private_key.pem";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // Render theo từng mode, không dùng switch-case nữa
  if (initialMode === "adminHome") {
    if (role !== "admin") {
      return <Navigate to="/login" replace />
    }

    return (
      <div key="adminHome">
        <p>Hello {fullName} (Admin)</p>
        <button onClick={goToChangePassword}>
          Change password
        </button>
        <button onClick={handleSignOut}>
          Sign out
        </button>
      </div>
    )
  }

  if (initialMode === "home") {
    return (
      <div key="home">
        <p>Hello {fullName}</p>
        <button onClick={goToChangePassword}>
          Change password
        </button>
        <button onClick={handleGenerateKey}>
          Generate Key
        </button>
        <button onClick={handleSignOut}> 
          Sign out
        </button>
      </div>
    )
  }

  if (initialMode === "signIn") {
    return (
      <Login
        name={name}
        password={password}
        onNameChange={handleName}
        onPasswordChange={handlePassword}
        onSignIn={handleSignIn}
      />
    )
  }

  if (initialMode === "signUp") {
    return (
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
    )
  }

  if (initialMode === "changePassword" || initialMode === "changePasswordPhase2") {
    return (
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
    )
  }

  return null;
}

// create handle vertify