    export default function SignIn({name, handleName, password, handlePassword, handleSignIn, handleMode})
    {
        return(
            <div id="signIn" key='signIn'>
                <div>
                    <input value={name} placeholder="Enter your user name here: " onChange={handleName} id="inputName"></input>
                    <input value={password} placeholder="Enter your password here: " onChange={handlePassword} id="inputEmail"></input>
                    <button value="home" id = "buttonSignIn" onClick={(e) => handleSignIn(e)}>Sign in</button>
                    <button value="signUp" id = "buttonSignUp" onClick={handleMode}>Sign up</button>
                    <button value = "changePassword" id = "buttonChangePassword" onClick={handleMode}>change password</button>
                </div>
                <div id="keyIcon">
                    <div className="shaftKey"></div>
                    <div className="headKey"></div>
                    <div className="teethKey"></div>
                </div>
            </div>
        )
    }