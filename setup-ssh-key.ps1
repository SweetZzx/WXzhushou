# SSH密钥配置脚本
$password = ConvertTo-SecureString "Zzx1359355146" -AsPlainText -Force
$pubkey = Get-Content $env:USERPROFILE\.ssh\id_rsa.pub

$command = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo `"$pubkey`" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'SSH密钥配置完成'"

ssh -o StrictHostKeyChecking=no root@47.110.242.66 $command
