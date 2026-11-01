param([string]$PostFile = 'posts/001-welcome.txt')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
$previousToken = $env:TELEGRAM_BOT_TOKEN
$secureToken = $null
$tokenPointer = [IntPtr]::Zero
try {
    if (-not $env:TELEGRAM_BOT_TOKEN) {
        $secureToken = Read-Host 'Токен бота (ввод скрыт)' -AsSecureString
        $tokenPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureToken)
        $env:TELEGRAM_BOT_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($tokenPointer)
    }
    go run . -file $PostFile -send
    if ($LASTEXITCODE -ne 0) { throw 'Публикация не подтверждена. Проверьте сообщение выше.' }
} finally {
    $env:TELEGRAM_BOT_TOKEN = $previousToken
    if ($tokenPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($tokenPointer) }
    if ($secureToken) { $secureToken.Dispose() }
    Pop-Location
}
