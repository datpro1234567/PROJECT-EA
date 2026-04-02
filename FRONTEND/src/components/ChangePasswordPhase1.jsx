export default function ChangePasswordPhase1({name, handleName, password, handlePassword, handleChangePasswordPhase1})
{
    return(
        <div id = "ChangePasswordPhase1" key="changePassword" >
            <input value={name} placeholder="Enter your userName: " onChange={handleName}></input>
            <input value={password} placeholder="Enter your password: " onChange={handlePassword}></input>
            <button value ="changePasswordPhase2" onClick={handleChangePasswordPhase1}>Confirm</button>
        </div>
    )
}