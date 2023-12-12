// vim: nofoldenable:

## Install argocd

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
sleep 60
argocd admin initial-password -n argocd
export argocd_server="172.18.0.4"
argocd login $argocd_server
argocd account update-password
# Password: Password
argocd cluster list
kubectl config set-context --current --namespace=argocd
argocd app create guestbook --repo https://github.com/argoproj/argocd-example-apps.git --path guestbook --dest-server https://kubernetes.default.svc --dest-namespace default
```

## Ref:
1. https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/
2. Complete application.yaml: https://argo-cd.readthedocs.io/en/stable/operator-manual/application.yaml
