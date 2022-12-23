import socket, select


def find_tracker():
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  retry = 0
  tracker = {}
  mac = [None]*6
  sock.bind(("0.0.0.0", 6969))
  print("트래커를 찾는 중..", end="", flush=True)
  try:
      while True:
          ready = select.select([sock], [], [], 0.2)
          if ready[0]:
              print("OK!")
              data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
              # print("received message: %s" % data)
              boardType = int.from_bytes(
                  data[0:4], byteorder='big', signed=False)
              # print("boardType: %d" % boardType)
              tracker['boardType'] = boardType
              imuType = int.from_bytes(data[4:8], byteorder='big', signed=False)
              # print("imuType: %d" % imuType)
              tracker['imuType'] = imuType
              mcuType = int.from_bytes(data[8:12], byteorder='big', signed=False)
              # print("mcuType: %d" % mcuType)
              tracker['mcuType'] = mcuType
              imuInfo = int.from_bytes(
                  data[12:16], byteorder='big', signed=False)
              # print("imuInfo: %d" % imuInfo)
              tracker['imuInfo'] = imuInfo
              data[16:20]
              data[20:24]
              firmwareBuild = int.from_bytes(
                  data[24:28], byteorder='big', signed=False)
              # print("firmwareBuild: %s" % firmwareBuild)
              tracker['firmwareBuild'] = firmwareBuild
              firmware = data[41:41+data[40]].decode('ascii')
              # print("firmware: %s" % firmware)
              tracker['firmware'] = firmware
              for i in range(0, 6):
                  mac[i] = data[41+data[40]+i]
              # print("mac: %02X:%02X:%02X:%02X:%02X:%02X" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]))
              tracker['mac'] = ("mac: %02X:%02X:%02X:%02X:%02X:%02X" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]))
              # print("ip: %s" % addr[0])
              tracker['ip'] = addr[0]
              break
              # time.sleep(1)
          else:
              print(".", end="", flush=True)
              retry += 1
              if retry > 50:
                  print("트래커를 찾을 수 없어요")
                  break
  except KeyboardInterrupt:
      print('취소됨')
  except Exception as e:
      print("트래커를 찾을 수 없어요 :", e)

  sock.close()
  return tracker
