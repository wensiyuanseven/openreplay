### Generate ssh key for github
ssh-keygen -t rsa -b 4096 -C "openreplay@argo.com"

### Add the SSH Public Key to GitHub

- Open the generated public key file (argo_cd_ssh_key.pub).
- Copy its content.
- Go to your GitHub account settings → SSH and GPG keys.
- Click "New SSH key", paste your key, and save.

### Create a Kubernetes Secret with the SSH Private Key

kubectl create secret generic my-github-ssh-key --from-file=sshPrivateKey=/path/to/argo_cd_ssh_key -n argocd

### Apply the Argo CD Configuration Application

kubectl apply -f argo-cd-config-app.yaml -n argocd
