import "./Register.css";
import "../Global.css";

export default function Register({
  name,
  fullName,
  password,
  cPassword,
  onNameChange,
  onFullNameChange,
  onPasswordChange,
  onCPasswordChange,
  onSignUp,
}) {
  return (
    <div id="signUp" key="signUp">
      <input
        value={fullName}
        placeholder="Enter your full name: "
        onChange={onFullNameChange}
      />
      <input
        value={name}
        placeholder="Create your user name: "
        onChange={onNameChange}
      />
      <input
        value={password}
        placeholder="Create your password: "
        onChange={onPasswordChange}
      />
      <input
        value={cPassword}
        placeholder="Confirm your password: "
        onChange={onCPasswordChange}
      />
      <button value="signIn" onClick={onSignUp}>
        Create
      </button>
    </div>
  );
}
