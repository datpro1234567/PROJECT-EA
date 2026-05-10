import "./ForgotPassword.css";
import "../Global.css";

export default function ForgotPassword({
  mode,
  name,
  password,
  cPassword,
  onNameChange,
  onPasswordChange,
  onCPasswordChange,
  onChangePassword,
  onChangePasswordPhase2,
}) {
  if (mode === "changePassword") {
    return (
      <div id="changePassword" key="changePassword">
        <input
          value={name}
          placeholder="Enter your userName: "
          onChange={onNameChange}
        />
        <input
          value={password}
          placeholder="Enter your password: "
          onChange={onPasswordChange}
        />
        <button value="changePasswordPhase2" onClick={onChangePassword}>
          Confirm
        </button>
      </div>
    );
  }

  if (mode === "changePasswordPhase2") {
    return (
      <div key="changePasswordPhase2">
        <input
          value={password}
          placeholder="Create your new password: "
          onChange={onPasswordChange}
        />
        <input
          value={cPassword}
          placeholder="Confirm your new password: "
          onChange={onCPasswordChange}
        />
        <button value="signIn" onClick={onChangePasswordPhase2}>
          Confirm
        </button>
      </div>
    );
  }

  return null;
}
