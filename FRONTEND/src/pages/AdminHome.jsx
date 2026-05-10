import "./Home.css";
import "../Global.css";

export default function AdminHome({ fullName, onChangePassword, onCreateRootCAKey, onSignOut }) {
  return (
    <div id="adminHome" key="adminHome">
      <p>Hello {fullName} (Admin)</p>
      <button onClick={onChangePassword}>
        Change password
      </button>
      <button onClick={onCreateRootCAKey}>
        Create Root CA key
      </button>
      <button onClick={onSignOut}>
        Sign out
      </button>
    </div>
  );
}
