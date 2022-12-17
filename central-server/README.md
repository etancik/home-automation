https://docs.fedoraproject.org/en-US/fedora-coreos/bare-metal/

https://docs.fedoraproject.org/en-US/fedora-coreos/producing-ign/

https://github.com/coreos/butane/releases

To change regenerate ignition file for the yaml config
```shell
butane --pretty --strict ignite.bu > ignite.ign
```
To serve ignition file
```shell
python3 -m http.server
```
After install
```shell
sudo rpm-ostree install docker-compose
sudo rpm-ostree install git
```
```shell
mkdir git && cd git
git init
git remote add -f origin https://github.com/etancik/home-automation.git
git sparse-checkout init
git sparse-checkout set "central-server/docker-compose/"
git pull origin master
```