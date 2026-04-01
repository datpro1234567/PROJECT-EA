export default function ChangePasswordPhase2({password, handlePassword, cPassword, handleCPassword, handleChangePasswordPhase2})
{
    return(
        <div key="changePasswordPhase2">
            <input value = {password} placeholder="Create your new password: " onChange ={handlePassword}></input>
            <input value = {cPassword} placeholder="Confirm your new password: "onChange={handleCPassword}></input>
            <button value = "signIn" onClick={handleChangePasswordPhase2}>Confirm</button>
        </div>
    )
}