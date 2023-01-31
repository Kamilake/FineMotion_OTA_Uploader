#!/usr/bin/env python3
# Original espota.py by Ivan Grokhotkov:
# https://gist.github.com/igrr/d35ab8446922179dc58c
# Modified since 2015-09-18 from Pascal Gollor (https://github.com/pgollor)
# Modified since 2015-11-09 from Hristo Gochkov (https://github.com/me-no-dev)
# Modified since 2016-01-03 from Matthew O'Gorman (https://githumb.com/mogorman)
# Modified since 2022-12-20 from Kamilake/Kamilake (https://githumb.com/Kamilake)

from __future__ import print_function
import socket
import sys
import select
import os
import optparse
import logging
import hashlib
import i18n
import locale
import ctypes
i18n.set('file_format', 'json')
i18n.set('filename_format', 'lang.json')
i18n.set('locale', locale.windows_locale[ ctypes.windll.kernel32.GetUserDefaultUILanguage() ])
# sys.stdout.write(i18n.get('locale'))
i18n.load_path.append(os.path.abspath('lang'))
# print(os.path.abspath('lang'))
# i18n.set('locale', "en")
try:
  i18n.t('hi')
except(i18n.loaders.loader.I18nFileLoadError):
  i18n.set('locale', 'en')
  sys.stdout.write("'ㅁ'!\n")
# print(i18n.t('hi'))

# Commands
FLASH = 0
SPIFFS = 100
AUTH = 200
PROGRESS = True
# BRANDNAME = "#BRANDNAME# #DEVICENAME#"
# DEVICENAME = "#TRACKERNAME# #DEVICENAME#"
# AUTHOR = "#AUTHORNAME#"
BRANDNAME = "FineMotion Tracker"
DEVICENAME = "FineMotion 트래커"
AUTHOR = "Kamilake"
VERSION = "0.1.0"

# define Python user-defined exceptions
class TrackerNotFoundException(Exception):
    "The device could not be detected within the specified timeout"
    pass
def find_tracker():
  sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
  retry = 0
  tracker = {}
  mac = [None]*6
  sock.bind(("0.0.0.0", 6969))
  sys.stdout.write(i18n.t('findingDevice',DEVICENAME=DEVICENAME)) #, end="", flush=True)
  try:
      while True:
          ready = select.select([sock], [], [], 0.2)
          if ready[0]:
              sys.stdout.write("OK!\n")
              data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
              try:
                boardType = int.from_bytes(
                    data[0:4], byteorder='big', signed=False)
                tracker['boardType'] = boardType
                imuType = int.from_bytes(data[4:8], byteorder='big', signed=False)
                tracker['imuType'] = imuType
                mcuType = int.from_bytes(data[8:12], byteorder='big', signed=False)
                tracker['mcuType'] = mcuType
                imuInfo = int.from_bytes(
                    data[12:16], byteorder='big', signed=False)
                tracker['imuInfo'] = imuInfo
                data[16:20]
                data[20:24]
                firmwareBuild = int.from_bytes(
                    data[24:28], byteorder='big', signed=False)
                tracker['firmwareBuild'] = firmwareBuild
                firmware = data[41:41+data[40]].decode('ascii')
                tracker['firmware'] = firmware
                for i in range(0, 6):
                    mac[i] = data[41+data[40]+i]
                tracker['mac'] = ("mac: %02X:%02X:%02X:%02X:%02X:%02X" % (mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]))
              except:
                    ''
              tracker['ip'] = addr[0]
              tracker['port'] = addr[1]
              break
          else:
              sys.stdout.write(".")  # , end="", flush=True)
              sys.stdout.flush()
              retry += 1
              if retry > 50:
                  raise TrackerNotFoundException(i18n.t('trackerNotFoundException',DEVICENAME=DEVICENAME))
                  break
  except KeyboardInterrupt:
      sys.stderr.write(i18n.t('interrupted'))
      sys.stderr.flush()
      sock.close()
      sys.stderr.write('OK!')
      sys.exit(0)
  sock.close()
  return tracker

# update_progress() : Displays or updates a console progress bar
## Accepts a float between 0 and 1. Any int will be converted to a float.
## A value under 0 represents a 'halt'.
## A value at 1 or bigger represents 100%
def update_progress(progress):
  if (True):
    barLength = 60 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
      progress = float(progress)
    if not isinstance(progress, float):
      progress = 0
      # status = "error: progress var must be float\r\n"
      status = i18n.t('progressMustBeFloat') + "\r\n"
    if progress < 0:
      progress = 0
      # status = "중단됨...\r\n"
      status = i18n.t('cancelled') + "\r\n"
    if progress >= 1:
      progress = 1
      # status = f"성공했어요!\r\n스스로 껏다 켜질 때까지 {DEVICENAME}의 전원을 끄지 말아주세요.\r\n"
      status = i18n.t('successButDontTurnOff',DEVICENAME=DEVICENAME) + "\r\n"
    block = int(round(barLength*progress))
    # text = "\r펌웨어를 올리고 있어요: [{0}] {1}% {2}".format( "="*block + " "*(barLength-block), int(progress*100), status)
    # "uploadingFirmware": "펌웨어를 올리고 있어요: %{PROGRESSBAR} %{PROGRESS}% %{STATUS}",
    text = i18n.t('uploadingFirmware',PROGRESSBAR="="*block + " "*(barLength-block),PROGRESS=int(progress*100),STATUS=status)
    sys.stderr.write("\r"+text)
    sys.stderr.flush()
  else:
    sys.stderr.write('.')
    sys.stderr.flush()

def serve(remoteAddr, localAddr, remotePort, localPort, password, filename, command = FLASH):
  # Create a TCP/IP socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_address = (localAddr, localPort)
  logging.info('Starting on %s:%s', str(server_address[0]), str(server_address[1]))
  try:
    sock.bind(server_address)
    sock.listen(1)
  except Exception:
    logging.error("Listen Failed")
    return 1

  # Check whether Signed Update is used.
  if ( os.path.isfile(filename + '.signed') ):
    filename = filename + '.signed'
    file_check_msg = 'Detected Signed Update. %s will be uploaded instead.' % (filename)
    sys.stderr.write(file_check_msg + '\n')
    sys.stderr.flush()
    logging.info(file_check_msg)
  
  content_size = os.path.getsize(filename)
  f = open(filename,'rb')
  file_md5 = hashlib.md5(f.read()).hexdigest()
  f.close()
  logging.info('Upload size: %d', content_size)
  message = '%d %d %d %s\n' % (command, localPort, content_size, file_md5)

  # Wait for a connection
  logging.info('Sending invitation to: %s', remoteAddr)
  sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  remote_address = (remoteAddr, int(remotePort))
  sock2.sendto(message.encode(), remote_address)
  sock2.settimeout(10)
  try:
    data = sock2.recv(128).decode()
  except Exception:
    logging.error(i18n.t('trackerNotFound'))
    sock2.close()
    return 1
  if (data != "OK"):
    if(data.startswith('AUTH')):
      nonce = data.split()[1]
      cnonce_text = '%s%u%s%s' % (filename, content_size, file_md5, remoteAddr)
      cnonce = hashlib.md5(cnonce_text.encode()).hexdigest()
      passmd5 = hashlib.md5(password.encode()).hexdigest()
      result_text = '%s:%s:%s' % (passmd5 ,nonce, cnonce)
      result = hashlib.md5(result_text.encode()).hexdigest()
      sys.stdout.write(i18n.t('recoveryModeInit',DEVICENAME=DEVICENAME))
      sys.stderr.flush()
      sys.stdout.flush()
      message = '%d %s %s\n' % (AUTH, cnonce, result)
      sock2.sendto(message.encode(), remote_address)
      sock2.settimeout(10)
      try:
        data = sock2.recv(32).decode()
      except Exception:
        sys.stderr.write(i18n.t('fail') + '\n')
        logging.error(i18n.t('trackerDidntRespond',DEVICENAME=DEVICENAME))
        # logging.error('전원을 켜고 1분 안으로 다시 시도해주세요.')
        logging.error(i18n.t('turnOnAndTryAgain'))
        sock2.close()
        return 1
      if (data != "OK"):
        # sys.stderr.write('실패\n')
        sys.stderr.write(i18n.t('fail') + '\n')
        logging.error('%s', data)
        sock2.close()
        sys.exit(1)
        return 1
      sys.stderr.write('OK\n')
    else:
      logging.error('Bad Answer: %s', data)
      sock2.close()
      return 1
  sock2.close()

  logging.info('Waiting for device...')
  try:
    sock.settimeout(10)
    connection, client_address = sock.accept()
    sock.settimeout(None)
    connection.settimeout(None)
  except Exception:
    # logging.error(f'{DEVICENAME}를 찾을 수 없어요. 방화벽이나 프록시 설정을 확인해주세요.')
    logging.error(i18n.t('recoveryModeDeviceNotFound',DEVICENAME=DEVICENAME))
    sock.close()
    return 1
  received_ok = False
  try:
    f = open(filename, "rb")
    if (PROGRESS):
      update_progress(0)
    else:
      sys.stderr.write('Uploading')
      sys.stderr.flush()
    offset = 0
    while True:
      chunk = f.read(1460)
      if not chunk: break
      offset += len(chunk)
      update_progress(offset/float(content_size))
      connection.settimeout(10)
      try:
        connection.sendall(chunk)
        if connection.recv(32).decode().find('O') >= 0:
          # connection will receive only digits or 'OK'
          received_ok = True
      except Exception:
        sys.stderr.write('\n')
        # logging.error('업로드에 실패했어요.')
        logging.error(i18n.t('uploadFailed'))
        connection.close()
        f.close()
        sock.close()
        return 1

    sys.stderr.write('\n')
    # logging.info('결과를 기다리는 중이에요...')
    logging.info(i18n.t('waitingForResult'))
    # libraries/ArduinoOTA/ArduinoOTA.cpp L311 L320
    # only sends digits or 'OK'. We must not not close
    # the connection before receiving the 'O' of 'OK'
    try:
      connection.settimeout(60)
      received_ok = False
      received_error = False
      while not (received_ok or received_error):
        reply = connection.recv(64).decode()
        # Look for either the "E" in ERROR or the "O" in OK response
        # Check for "E" first, since both strings contain "O"
        if reply.find('E') >= 0:
          sys.stderr.write('\n')
          logging.error('%s', reply)
          received_error = True
        elif reply.find('O') >= 0:
          logging.info('Result: OK')
          received_ok = True
      connection.close()
      f.close()
      sock.close()
      if received_ok:
        return 0
      return 1
    except Exception:
      logging.error('No Result!')
      connection.close()
      f.close()
      sock.close()
      return 1

  finally:
    connection.close()
    f.close()

  sock.close()
  return 1
# end serve


def parser(unparsed_args):
  parser = optparse.OptionParser(
    usage = "%prog [options]",
    description = "Transmit image over the air to the esp8266 module with OTA support."
  )

  # destination ip and port
  group = optparse.OptionGroup(parser, "Destination")
  group.add_option("-i", "--ip",
    dest = "esp_ip",
    action = "store",
    help = "ESP8266 IP Address.",
    default = False
  )
  group.add_option("-I", "--host_ip",
    dest = "host_ip",
    action = "store",
    help = "Host IP Address.",
    default = "0.0.0.0"
  )
  group.add_option("-p", "--port",
    dest = "esp_port",
    type = "int",
    help = "ESP8266 ota Port. Default 8266",
    default = 8266
  )
  group.add_option("-P", "--host_port",
    dest = "host_port",
    type = "int",
    help = "Host server ota Port. Default random 10000-60000",
    default = 6969
  )
  parser.add_option_group(group)

  # auth
  group = optparse.OptionGroup(parser, "Authentication")
  group.add_option("-a", "--auth",
    dest = "auth",
    help = "Set authentication password.",
    action = "store",
    default = "SlimeVR-OTA"
  )
  parser.add_option_group(group)

  # image
  group = optparse.OptionGroup(parser, "Image")
  group.add_option("-f", "--file",
    dest = "image",
    help = "Image file.",
    metavar="FILE",
    default = None
  )
  group.add_option("-s", "--spiffs",
    dest = "spiffs",
    action = "store_true",
    help = "Use this option to transmit a SPIFFS image and do not flash the module.",
    default = False
  )
  parser.add_option_group(group)

  # output group
  group = optparse.OptionGroup(parser, "Output")
  group.add_option("-d", "--debug",
    dest = "debug",
    help = "Show debug output. And override loglevel with debug.",
    action = "store_true",
    default = False
  )
  group.add_option("-r", "--progress",
    dest = "progress",
    help = "Show progress output. Does not work for ArduinoIDE",
    action = "store_true",
    default = False
  )
  parser.add_option_group(group)

  (options, args) = parser.parse_args(unparsed_args)

  return options
# end parser


def main(args):
  # get options
  options = parser(args)
  sys.stderr.write(f"{BRANDNAME} OTA Uploader v1.0.0 by {AUTHOR}\n")

  # adapt log level
  loglevel = logging.WARNING
  if (options.debug):
    loglevel = logging.DEBUG
  # end if

  # logging
  logging.basicConfig(level = loglevel, format = '%(asctime)-8s [%(levelname)s]: %(message)s', datefmt = '%H:%M:%S')

  logging.debug("Options: %s", str(options))

  # check options
  global PROGRESS
  PROGRESS = True

  try:
    sock4 = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock4.bind(("0.0.0.0", 6969))
    sock4.close()
  except:
    sys.stderr.write(i18n.t('serverAlreadyRunning')+"\n")
    sys.stderr.write(i18n.t('pleaseCloseServerAndRunAgain')+"\n")
    input(i18n.t('pressAnyKeyToExit'))
    sys.exit(0)


  if (not options.image):
    while(True):
      try:
        sys.stdout.write(i18n.t('pleaseSelectImageFile'))
        #show ./img list
        files=os.walk(".\img").__next__()[2]
        i=0
        for filename in files:
          if filename.endswith(".bin"):
            sys.stdout.write(str(i)+") "+filename.replace(".bin","") +"\n")
          i+=1
        #end for
        sys.stdout.write(i18n.t('pleaseInputNumber'))
        options.image = ".\img\\"+files[int(input())]
        sys.stdout.write(i18n.t('selectedFileIs',FILENAME=options.image)+"\n")
        break
      except IndexError:
        sys.stderr.write("\n"+i18n.t('pleaseTypeAgain')) 
        continue
      except ValueError:
        sys.stderr.write("\n"+i18n.t('pleaseTypeAgain'))
        continue
      except KeyboardInterrupt:
        sys.stderr.write(i18n.t('interrupted'))
        sys.stderr.flush()
        # nothing to clean up
        sys.stderr.write('OK!')
        sys.exit(0)

  if (not options.esp_ip):
    while(True):
      # # logging.critical("Not enough arguments.")
      # sys.stderr.write(f"먼저, {DEVICENAME}의 전원을 켠 다음 SlimeVR 서버로 IP주소를 찾아주세요.\n")
      # sys.stderr.write("SlimeVR 서버에서 IP 주소가 표시되나요? ( udp:// 숫자 )\n")
      # sys.stderr.write(f"그렇다면, 연결하려는 {DEVICENAME}의 IP 주소를 입력해주세요: ")
      # options.esp_ip = input()
      # sys.stdout.write(f"업데이트하기 전에, 업데이트하려는 {DEVICENAME}의 전원을 켜주세요!\n")
      sys.stdout.write(i18n.t('pleaseTurnOnPowerOfDevice',DEVICENAME=DEVICENAME)+"\n")
      try:
        tracker = find_tracker()
        break
      except TrackerNotFoundException as e:
        sys.stderr.write(str(e)+"\n")
        # sys.stderr.write("다시 시도하려면 엔터를 눌러주세요. 종료하려면 Ctrl+C를 눌러주세요...\n")
        sys.stderr.write(i18n.t('pleasePressEnterOrCtrlC')+"\n")
        input()
    options.esp_ip = str(tracker['ip'])
    # sys.stdout.write(f"{DEVICENAME}의 IP 주소: "+options.esp_ip+"\n")
    sys.stdout.write(i18n.t('deviceIP',DEVICENAME=DEVICENAME,IP=options.esp_ip)+"\n")
    
  # end if
  
  # sys.stdout.write("업데이트를 시작할게요. 잠시만 기다려주세요.\n")
  # sys.stderr.write("업데이트 중에 전원을 끄지 말아주세요\n")

  sys.stdout.write(i18n.t('startUpdate')+"\n")
  sys.stderr.write(i18n.t('doNotTurnOffPower')+"\n")

  command = FLASH
  if (options.spiffs):
    command = SPIFFS
  # end if
  try:
   serve(options.esp_ip, options.host_ip, options.esp_port, options.host_port, options.auth, options.image, command)
  except KeyboardInterrupt:
    # sys.stderr.write(f"업로드를 중단할게요. {DEVICENAME}는 원래대로 돌아갔어요\n")
    sys.stderr.write(i18n.t('uploadInterrupted',DEVICENAME=DEVICENAME)+"\n")
  except Exception as e:
    # sys.stderr.write("업로드 중 오류가 발생했어요: "+str(e)+"\n")
    sys.stderr.write(i18n.t('uploadError',ERROR=str(e))+"\n")

# end main


if __name__ == '__main__':
  sys.exit(main(sys.argv))
# end if
