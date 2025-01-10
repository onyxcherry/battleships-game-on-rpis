# Battleships game on Raspberry Pi

Battleship game played on Raspberry Pi Zero 2W and LED RGB matrices

## Setup

### Requirements

- Python 3.11+ installed
- pip
- sudo privileges (e.g. for gpio)
- nmcli (network-manager installed)

### Code setup

1. Clone the code

    ```shell
    sudo git clone https://github.com/onyxcherry/battleships-game-on-rpis.git /battleships-game-on-rpis
    ```

    > replace `rpiuser` with your username!

    ```shell
    sudo chown -R rpiuser:rpiuser /battleships-game-on-rpis
    ```

2. Install requirements

   ```shell
   cd /battleships-game-on-rpis && python3 -m venv venv && source venv/bin/activate
   ```

   ```shell
   pip install wheel -r requirements.txt
   ```

### Access Point setup

1. Add `battleships` connection

    ```shell
    sudo nmcli con add type wifi ifname wlan0 con-name battleships autoconnect yes ssid battleships mode ap ipv4.method shared connection.autoconnect-priority 200
    ```

2. Set the password

    ```shell
    nmcli con modify battleships wifi-sec.key-mgmt wpa-psk
    ```

    > replace the password with your own

    ```shell
    nmcli con modify battleships wifi-sec.psk "veryveryhardpassword1234"
    ```

3. Make the AP running

    ```shell
    nmcli con up battleships
    ```

4. Verify the AP has been created successfully

    List active connections

    ```shell
    nmcli -f NAME,UUID,AUTOCONNECT,AUTOCONNECT-PRIORITY c
    ```

### Connect to the AP

Now, you should be able to connect to hostname _battleships_ via WiFi with the provided password.

Run

```shell
sudo nmcli device wifi connect battleships password veryveryhardpassword1234
```

### Server unit service file

In order to run and manage battleships game server automatically, run the server at **one device**

```shell
mkdir -p ~/.config/systemd/user/
```

```shell
cp /battleships-game-on-rpis/infra/server.service ~/.config/systemd/user/battleships-server.service
```

```shell
loginctl enable-linger
```

```shell
systemctl --user daemon-reload && systemctl --user start battleships-server.service && systemctl --user enable battleships-server.service
```

---

See the server status by `systemctl --user status battleships-server.service`  
or journal logs by `journalctl --user -u battleships-server.service`

### Client system service file

Run the client **on both devices**

```shell
sudo cp /battleships-game-on-rpis/infra/client.service /etc/systemd/system/battleships-client.service
```

```shell
touch /battleships-game-on-rpis/client-logs /battleships-game-on-rpis/client-error-logs && chmod a+wr /battleships-game-on-rpis/client-*
```

```shell
sudo loginctl enable-linger
```

```shell
sudo systemctl daemon-reload && sudo systemctl start battleships-client.service && sudo systemctl enable battleships-client.service
```

LED matrices should light up now.
