param([Parameter(Mandatory=$true)][string]$InstallDir,[Parameter(Mandatory=$true)][string]$LogFile)
$ErrorActionPreference='Stop'
$events=New-Object System.Collections.Generic.List[string]
try {
 $root=[IO.Path]::GetFullPath($InstallDir).TrimEnd('\')
 $runtime=Join-Path $root 'John\runtime'
 $allowed=@('launch_john.py','suite_john.py','file_mailbox.py','john_connexion.py')
 function RuntimeProcesses {
  @(Get-CimInstance Win32_Process | Where-Object {$_.ExecutablePath -and ($_.ExecutablePath -ieq (Join-Path $runtime 'pythonw.exe') -or $_.ExecutablePath -ieq (Join-Path $runtime 'python.exe'))})
 }
 function KnownScript($proc) {
  foreach($script in $allowed){
   $scriptPath=Join-Path $root ('John\'+$script)
   if($proc.CommandLine -match ('(?i)(?:^|[\s"])(?:'+[regex]::Escape($scriptPath)+')(?:"|\s|$)')){return $true}
  }
  return $false
 }
 # Graceful closure lets the companion stop its owned gateway normally.
 $running=RuntimeProcesses
 foreach($proc in $running){
  if(!(KnownScript $proc)){continue}
  $live=Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
  if(!$live -or $live.Path -ine $proc.ExecutablePath){continue}
  if($live.MainWindowHandle -ne 0){[void]$live.CloseMainWindow();[void]$live.WaitForExit(5000)}
 }
 $running=RuntimeProcesses
 foreach($proc in $running){
  if(!(KnownScript $proc)){throw "An independent Python process is active (PID $($proc.ProcessId)). Close John before retrying. The gateway was not stopped by this script."}
 }
 foreach($proc in $running){
  $live=Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
  if(!$live){continue}
  if($live.Path -ine $proc.ExecutablePath){throw 'Process identity changed; retry.'}
  if(!$live.HasExited){$live.Kill();if(!$live.WaitForExit(5000)){throw 'Companion did not stop.'}}
  $events.Add("Stopped companion PID $($proc.ProcessId)")
 }
 if(Test-Path $runtime){
  foreach($file in (Get-ChildItem $runtime -File | Where-Object {$_.Name -match '^python.*\.(dll|exe)$'})){
   $stream=[IO.File]::Open($file.FullName,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
   $stream.Dispose()
  }
 }
 foreach($name in @('PC_Sentinelle_V32.exe','PC_Sentinelle_V32.dll')){
  $path=Join-Path $root ('PC\'+$name)
  if(Test-Path $path){$stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$stream.Dispose()}
 }
 $events.Add('PREFLIGHT_OK - files available; V24 code untouched.')
 $events | Set-Content -LiteralPath $LogFile -Encoding UTF8
 exit 0
} catch {
 $events.Add('PREFLIGHT_ERROR: '+$_.Exception.Message)
 $events | Set-Content -LiteralPath $LogFile -Encoding UTF8
 exit 1
}
