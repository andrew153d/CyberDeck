
#install readsb and tar1090 for ABS-b tracking
sudo apt install curl
sudo bash -c "$(wget -O - https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh)"
sudo bash -c "$(wget -nv -O - https://github.com/wiedehopf/tar1090/raw/master/install.sh)"
#go ahead and disable the services, start them when needed
sudo systemctl disable tar1090.service
sudo systemctl disable readsb.service
