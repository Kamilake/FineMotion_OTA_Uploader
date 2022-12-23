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
import os
import optparse
import logging
import hashlib
import discover

# Commands
FLASH = 0
SPIFFS = 100
AUTH = 200
PROGRESS = True
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
      status = "error: progress var must be float\r\n"
    if progress < 0:
      progress = 0
      status = "중단됨...\r\n"
    if progress >= 1:
      progress = 1
      status = "성공했어요!\r\n스스로 껏다 켜질 때까지 트래커의 전원을 끄지 말아주세요.\r\n"
    block = int(round(barLength*progress))
    text = "\r펌웨어를 올리고 있어요: [{0}] {1}% {2}".format( "="*block + " "*(barLength-block), int(progress*100), status)
    sys.stderr.write(text)
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
    logging.error('트래커를 찾을 수 없어요')
    logging.error('트래커가 켜져 있는지 확인해주세요.')
    logging.error('켜져 있다면 Wi-Fi에 연결될 때까지 기다리거나 IP 주소가 바뀌었는지 확인해주세요.')
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
      sys.stderr.write('트래커를 복구 모드로 바꿀게요...')
      sys.stderr.flush()
      message = '%d %s %s\n' % (AUTH, cnonce, result)
      sock2.sendto(message.encode(), remote_address)
      sock2.settimeout(10)
      try:
        data = sock2.recv(32).decode()
      except Exception:
        sys.stderr.write('실패\n')
        logging.error('트래커가 응답하지 않았어요.')
        logging.error('전원을 켜고 1분 안으로 다시 시도해주세요.')
        sock2.close()
        return 1
      if (data != "OK"):
        sys.stderr.write('실패\n')
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
    logging.error('No response from device')
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
        logging.error('업로드에 실패했어요.')
        connection.close()
        f.close()
        sock.close()
        return 1

    sys.stderr.write('\n')
    logging.info('결과를 기다리는 중이에요...')
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

  # if sys.argv[-1] != ASADMIN:
  #   script = os.path.abspath(sys.argv[0])
  #   params = ' -E '.join([script] + sys.argv[1:] + [ASADMIN])
  #   win32com.shell.shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
  #   sys.stderr.write("sys.executable: " + sys.executable + "\nlpParameters: " + params)
  #   sys.exit(0)

  if sys.argv[-1] == 'Firewall_on':
    # netsh.exe advfirewall set publicprofile state on
    import subprocess
    subprocess.check_call('netsh.exe advfirewall set publicprofile state on')
    subprocess.check_call('netsh.exe advfirewall set privateprofile state on')
    sys.exit(0)

  if sys.argv[-1] == 'Firewall_off':
    # netsh.exe advfirewall set publicprofile state off
    import subprocess
    subprocess.check_call('netsh.exe advfirewall set publicprofile state off')
    subprocess.check_call('netsh.exe advfirewall set privateprofile state off')
    sys.exit(0)
  sys.stderr.write("FineMotion Tracker OTA Uploader v1.0.0\n")

  # sys.stderr.write("====================================\n")
  # sys.stderr.write("ESP8266의 특성 때문에 OTA 업데이트를 위해서 잠시 방화벽의 모든 포트를 열어야 해요. \n")
  # sys.stderr.write("업데이트가 끝나면 자동으로 원래대로 돌려 놓을게요\n")
  # sys.stderr.write("괜찮으시겠어요? 원하지 않는다면 Ctrl+C를 눌러주세요\n")
  # sys.stderr.write("====================================\n")



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
    sys.stderr.write("SlimeVR 서버가 실행되고 있는 모양이에요.\n")
    sys.stderr.write("SlimeVR 서버를 종료하고 다시 실행해주세요.\n")
    input("종료하려면 아무 키나 눌러주세요...")
    sys.exit(0)



  if (not options.image):
    sys.stderr.write("\n업로드할 이미지 파일을 선택해주세요\n")
    #show ./img list
    files=os.walk(".\img").__next__()[2]
    i=0
    for filename in files:
      sys.stderr.write(str(i)+") "+filename+"\n")
      i+=1
    #end for
    sys.stderr.write("번호를 입력해주세요: ")
    options.image = ".\img\\"+files[int(input())]
    sys.stderr.write("선택한 파일: "+options.image+"\n")

  if (not options.esp_ip):
    # logging.critical("Not enough arguments.")
    # sys.stderr.write("먼저, 트래커의 전원을 켠 다음 SlimeVR 서버로 IP주소를 찾아주세요.\n")
    # sys.stderr.write("SlimeVR 서버에서 IP 주소가 표시되나요? ( udp:// 숫자 )\n")
    # sys.stderr.write("그렇다면, 연결하려는 트래커의 IP 주소를 입력해주세요: ")
    # options.esp_ip = input()
    sys.stderr.write("업데이트하기 전에, 업데이트하려는 트래커의 전원을 켜주세요!\n")
    # input("업데이트를 시작하려면 아무 키나 눌러주세요...")
    tracker = discover.find_tracker()
    options.esp_ip = str(tracker['ip'])
    sys.stderr.write("트래커의 IP 주소: "+options.esp_ip+"\n")

    
  # end if
  
  sys.stderr.write("업데이트를 시작할게요. 잠시만 기다려주세요.\n")
  sys.stderr.write("업데이트 중에 전원을 끄지 말아주세요\n")

  command = FLASH
  if (options.spiffs):
    command = SPIFFS
  # end if



  # import win32com.shell.shell
  # script = os.path.abspath(sys.argv[0])
  # params = ' '.join(['-E']+[script] + sys.argv[1:] + ['Firewall_off'])
  # win32com.shell.shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)

  try:
   serve(options.esp_ip, options.host_ip, options.esp_port, options.host_port, options.auth, options.image, command)
  except KeyboardInterrupt:
    sys.stderr.write("업로드를 중단할게요. 트래커는 원래대로 돌아갔어요\n")
  except Exception as e:
    sys.stderr.write("업로드 중 오류가 발생했어요: "+str(e)+"\n")

  # script = os.path.abspath(sys.argv[0])
  # params = ' '.join(['-E']+[script] + sys.argv[1:] + ['Firewall_on'])
  # win32com.shell.shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params)
  


# end main


if __name__ == '__main__':
  sys.exit(main(sys.argv))
# end if
