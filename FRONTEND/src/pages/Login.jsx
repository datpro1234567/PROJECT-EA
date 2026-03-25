import "./Login.css";
import "../Global.css";
import { Link } from "react-router-dom";

export default function Login({ name, password, onNameChange, onPasswordChange, onSignIn, onChangeMode }) {
  return (
    <div id="signIn" key="signIn">
      <div>
        <input
          value={name}
          placeholder="Enter your user name here: "
          onChange={onNameChange}
          id="inputName"
        />
        <input
          value={password}
          placeholder="Enter your password here: "
          onChange={onPasswordChange}
          id="inputEmail"
        />
        <button value="home" id="buttonSignIn" onClick={onSignIn}>
          Sign in
        </button>
        <Link to="/signup">
          <button value="signUp" id="buttonSignUp">
            Sign up
          </button>
        </Link>
        <Link to="/change-password">
          <button id="buttonChangePassword">
            change password
          </button>
        </Link>
      </div>
      <div id="keyIcon">
        <div className="shaftKey" />
        <div className="headKey" />
        <div className="teethKey" />
      </div>
    </div>
  );
}
