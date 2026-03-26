import { Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import Home from "./pages/Home";
import AdminHome from "./pages/AdminHome";
import { useAppLogic } from "./hooks/useAppLogic";

export default function App({ initialMode = "signIn" }) {
  const {
    name,
    fullName,
    password,
    cPassword,
    userId,
    role,
    handleName,
    handleFullName,
    handlePassword,
    handleCPassword,
    handleSignIn,
    handleSignUp,
    handleChangePassword,
    handleChangePasswordPhase2,
    handleSignOut,
    goToChangePassword,
    handleGenerateKey,
    handleCreateRootCAKey,
  } = useAppLogic(initialMode)

  if (initialMode === "adminHome") {
    if (role !== "admin") {
      return <Navigate to="/login" replace />
    }

    return (
      <AdminHome
        fullName={fullName}
        onChangePassword={goToChangePassword}
        onCreateRootCAKey={handleCreateRootCAKey}
        onSignOut={handleSignOut}
      />
    )
  }

  if (initialMode === "home") {
    if (!userId) {
      return <Navigate to="/login" replace />
    }
    return (
      <Home
        fullName={fullName}
        onChangePassword={goToChangePassword}
        onGenerateKey={handleGenerateKey}
        onSignOut={handleSignOut}
      />
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