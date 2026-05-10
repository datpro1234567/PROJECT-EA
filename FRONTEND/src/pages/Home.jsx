import "./Home.css";
import "../Global.css";

export default function Home({ fullName, onChangePassword, onGenerateKey, onSignOut }) {
  return (
    <div id="home" key="home">
      <p>Hello {fullName}</p>
      <button onClick={onChangePassword}>
        Change password
      </button>
      <button onClick={onGenerateKey}>
        Generate Key
      </button>
      <button onClick={onSignOut}>
        Sign out
      </button>
    </div>
  );
}
