# import socket, select

# def find_tracker():
#   sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#   retry = 0
#   tracker = {}
#   mac = [None]*6
#   sock.bind(("0.0.0.0", 6969))
#   print("트래커를 찾는 중..", end="", flush=True)
#   try:
#       while True:
#           ready = select.select([sock], [], [], 0.2)
#           if ready[0]:
#               print("OK!")
#               data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
#               try:
#                 boardType = int.from_bytes(
#                     data[0:4], byteorder='big', signed=False)
#                 tracker['boardType'] = boardType
#                 imuType = int.from_bytes(data[4:8], byteorder='big', signed=False)
#                 tracker['imuType'] = imuType
#                 mcuType = int.from_bytes(data[8:12], byteorder='big', signed=False)
#                 tracker['mcuType'] = mcuType
#                 imuInfo = int.from_bytes(
#                     data[12:16], byteorder='big', signed=False)
#                 tracker['imuInfo'] = imuInfo
#                 data[16:20]
#                 data[20:24]
#                 firmwareBuild = int.from_bytes(
#                     data[24:28], byteorder='big', signed=False)
#                 tracker['firmwareBuild'] = firmwareBuild
#                 firmware = data[41:41+data[40]].decode('ascii')
#                 tracker['firmware'] = firmware
#                 for i in range(0, 6):
#                     mac[i] = data[41+data[40]+i]
#                 tracker['mac'] = ("mac: %02X:%02X:%02X:%02X:%02X:%02X" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]))
#               except:
#                     ''
#               tracker['ip'] = addr[0]
#               tracker['port'] = addr[1]
#               break
#           else:
#               print(".", end="", flush=True)
#               retry += 1
#               if retry > 50:
#                   print("트래커를 찾을 수 없어요")
#                   break
#   except KeyboardInterrupt:
#       print('취소됨')
#   except Exception as e:
#       print("트래커를 찾을 수 없어요 :", e)
#   sock.close()
#   return tracker
