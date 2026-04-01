export default function SignUp({name, handleName, password, handlePassword, cPassword, handleCPassword, handleSignUp})
{
    return(
        <div id = "signUp" key="signUp">
            <input value = {name} placeholder="Create your user name: " onChange={handleName}></input>
            <input value = {password} placeholder="Create your password: " onChange={handlePassword}></input>
            <input value = {cPassword} placeholder="Confirm your password: " onChange={handleCPassword}></input>
            <button value="signIn" onClick={(e) => 
                {handleSignUp(e)}}>
                Create
            </button> 
        </div>
    )
}