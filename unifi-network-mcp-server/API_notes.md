# Change radio channel, found internal call

```
curl 'https://192.168.10.1/proxy/network/api/s/default/rest/device/6977b47012ba196953c77677' \
  -X 'PUT' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'content-type: application/json' \
  -b 'TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiIwYjc3MDZiOC1iMjU1LTQwODItYTE3Ny1jNDE5YjlhZDUwNmEiLCJwYXNzd29yZFJldmlzaW9uIjowLCJpc1JlbWVtYmVyZWQiOnRydWUsImNzcmZUb2tlbiI6IjExOWQwYjRiLWMzZWEtNDI1Zi1iNWJlLTc2M2IxZjEzOTI5NyIsImlhdCI6MTc3MDI0ODMxMywiZXhwIjoxNzcyODQwMzEzLCJqdGkiOiJjNGUxZDk0ZS0yYzgyLTQ2OTMtYTIyYS02MGYxZjk5MTE4M2UifQ.MTQ6fIm5STiPSUV4xgeUg2jqBMSOpPFoVPOsm4nNiDA; JSESSIONID=B6EA2462840965A2E796DEAE5F3B0ED8' \
  -H 'origin: https://192.168.10.1' \
  -H 'priority: u=1, i' \
  -H 'sec-ch-ua: "Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36' \
  -H 'x-csrf-token: 119d0b4b-c3ea-425f-b5be-763b1f139297' \
  --data-raw '{"name":"U7 Pro XG Wall","snmp_contact":"","snmp_location":"","mgmt_network_id":"66752c8c2b50d57f73e3008a","afc_enabled":false,"outdoor_mode_override":"default","led_override":"on","led_override_color":"#0000ff","led_override_color_brightness":100,"atf_enabled":false,"config_network":{"type":"dhcp","bonding_enabled":false},"mesh_sta_vap_enabled":false,"radio_table":[{"antenna_id":-1,"antenna_gain":4,"name":"wifi0","ht":20,"channel":6,"tx_power_mode":"auto","vwire_enabled":true,"min_rssi_enabled":false,"assisted_roaming_enabled":false,"radio":"ng"},{"antenna_id":-1,"antenna_gain":6,"name":"wifi1","ht":40,"channel":"auto","tx_power_mode":"auto","vwire_enabled":true,"min_rssi_enabled":false,"assisted_roaming_enabled":false,"radio":"na"},{"antenna_id":-1,"antenna_gain":6,"name":"wifi2","ht":160,"channel":"auto","tx_power_mode":"auto","vwire_enabled":true,"min_rssi_enabled":false,"assisted_roaming_enabled":false,"radio":"6e"}]}' \
  --insecure
  ```
  Need to find the device ID, it's not the one you can find with `https://192.168.10.1/proxy/network/integration/v1/sites/{siteId}/devices`