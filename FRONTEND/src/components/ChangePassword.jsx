export default function ChangePassword({name, handleName, password, handlePassword, handleChangePassword})
{
    return(
        <div id = "changePassword" key="changePassword" >
            <input value={name} placeholder="Enter your userName: " onChange={handleName}></input>
            <input value={password} placeholder="Enter your password: " onChange={handlePassword}></input>
            <button value ="changePasswordPhase2" onClick={handleChangePassword}>Confirm</button>
        </div>
    )
}