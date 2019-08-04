"""Import required libraries"""
import socket
import time
from datetime import datetime
import multiprocessing


"""Handles errors and print them to file"""
def errorHandler(code):
    """
    args: code in string format
    """
    error_timestamp = str(datetime.utcnow())
    
    if (code == '1a'):
        error_msg = "ERROR : Socket connection error. Reconnecting..."
    elif (code == '1b'):
        error_msg = "ERROR : Message length received is zero at socket"
    elif (code == '1c'):
        error_msg = "ERROR : There is no margin at 16384 buffer length"
    elif (code == '1d'):
        error_msg = "ERROR : Parent send error"
    elif (code == '1e'):
        error_msg = "ERROR : Parent receive error"
    elif (code == '2a'):
        error_msg = "ERROR : Decode receive error"
    elif (code == '2b'):
        error_msg = "ERROR : Decode send error"
    elif (code == '3a'):
        error_msg = "ERROR : Endpoint receive error"
    elif (code == '3b'):
        error_msg = "ERROR : Endpoint write error"
        
    error_msg_printed = ("%s : %s\n" %(error_timestamp, error_msg))
        
    with open("0_Log_Errors.txt", "a") as text_file:
        text_file.write(error_msg_printed)
        
    return


"""Set of necessary functions to obtain downlink format"""
def hex2bin(hexstr):
    """Convert a hexdecimal string to binary string, with zero fillings. """
    num_of_bits = len(hexstr) * 4
    binstr = bin(int(hexstr, 16))[2:].zfill(int(num_of_bits))
    return binstr
def bin2int(binstr):
    """Convert a binary string to integer. """
    return int(binstr, 2)
def df(msg):
    """Decode Downlink Format value, bits 1 to 5."""
    msgbin = hex2bin(msg)
    return min( bin2int(msgbin[0:5]) , 24 )


"""Function to obtain Squawk code from message"""
def idcode(msg):
    mbin = hex2bin(msg)
    C1 = mbin[19]
    A1 = mbin[20]
    C2 = mbin[21]
    A2 = mbin[22]
    C4 = mbin[23]
    A4 = mbin[24]
    # _ = mbin[25]
    B1 = mbin[26]
    D1 = mbin[27]
    B2 = mbin[28]
    D2 = mbin[29]
    B4 = mbin[30]
    D4 = mbin[31]
    byte1 = int(A4+A2+A1, 2)
    byte2 = int(B4+B2+B1, 2)
    byte3 = int(C4+C2+C1, 2)
    byte4 = int(D4+D2+D1, 2)
    return str(byte1) + str(byte2) + str(byte3) + str(byte4)


"""Function to convert time_hex to a readable decimal timestamp"""
def num_timestamp(time_hex):
    scale = 16                  # base 16, hexadecimal
    num_of_bits = 48            # 6 bytes = 6 x 8 = 48 bits
    
    # Convert to binary with leading zeros:
    binary_data = bin(int(time_hex, scale))[2:].zfill(num_of_bits)
    
    # Extract and convert for seconds and nanoseconds:
    s = binary_data[:18]
    ns = binary_data[18:]
    s = int(s, 2);
    ns = int(ns, 2);
    ts = str("%d.%d" %(s,ns))   # string concatonation
    
    # Typecast string to float/ decimal:
    ts_float = float(ts)
    return ts_float


"""Process that extracts and decodes complete messages"""
def decoder(decode_start, decode_end):
    '''
    <esc> "1" : 6 byte MLAT timestamp, 1 byte signal level, 2 byte Mode-AC
    <esc> "2" : 6 byte MLAT timestamp, 1 byte signal level, 7 byte Mode-S short frame
    <esc> "3" : 6 byte MLAT timestamp, 1 byte signal level, 14 byte Mode-S long frame
    <esc> "4" : 6 byte MLAT timestamp, status data, DIP switch configuration settings (not on Mode-S Beast classic)
    <esc><esc>: true 0x1a
    <esc> is 0x1a, and "1", "2" and "3" are 0x31, 0x32 and 0x33
    timestamp: wiki.modesbeast.com/Radarcape:Firmware_Versions#The_GPS_timestamp
    '''

    # Initialize variables:
    run_decoder = True          # process control flag
    decoder_message_count = 0   # keep count number of decoded messages

    while run_decoder:
        try:

            # Receive from parent process:
            try:
                completed_msg_list = decode_start.recv()
            except Exception as e:
                errorHandler('2a')
                
            messages_to_write = []  # List to contain messages (msg_to_write, in list form)
            msg_to_write = []       # Individual messages in list form
            
            # Loop through list of messages (in list form):
            for message in completed_msg_list:

                # Decode message type and extract payload from message:
                msgtype = message[0]
                if msgtype == 0x32:
                    # Mode-S Short Message, 7 byte, 14-len hexstr
                    payload = ''.join('%02X' % i for i in message[8:15])
                elif msgtype == 0x33:
                    # Mode-S Long Message, 14 byte, 28-len hexstr
                    payload = ''.join('%02X' % i for i in message[8:22])
                    # Added to handle Mode-AC:
                elif msgtype == 0x31:
                    # Mode-AC, 9 byte, 18-len hexstr
                    payload = ''.join('%02X' % i for i in message[8:10])
                else:
                    # Other message tupe
                    continue

                # incomplete message, control returned to top of for loop:
                if len(payload) not in [4, 14, 28]:
                    continue
                # # more secured alternative (only for mode S):
                # df = df(payload)
                # # skip incomplete message
                # if df in [0, 4, 5, 11] and len(payload) != 14:
                    # continue
                # if df in [16, 17, 18, 19, 20, 21, 24] and len(payload) != 28:
                    # continue

                # Extract hexadecimal string signifying the timestamp from full_message:
                # Method is common for all three message types above
                time_hex = ''.join('%02X' % i for i in message[1:7])
                
                # Call function to decode for timestamp in decimal/ float form:
                ts = num_timestamp(time_hex)
                
                # Extract full message:
                full_message = ''.join('%02X' % i for i in message[:])
                
                # Call function to decode for downlink format:
                downlink = df(payload)  # Garbage for mode A-C
                
                # Get Internet timestamp:
                utc_now = datetime.utcnow()
                utc_midnight = utc_now
                localtime = (utc_now - utc_midnight.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

                # First, check if len = 4 (mode-AC):
                if (len(payload)==4):
                    # Format list to contain data:
                    msg_to_write = [full_message, time_hex, ts, localtime, downlink, payload]   # squawk for mode AC taken to be just 'payload', a 2 byte message
                    # Append to list of formatted messages for writing:
                    messages_to_write.append(msg_to_write)

                # Call function to decode for squawk if DF5, 17, 21. For more supported functions, see 'extra':
                elif (downlink in [5, 17, 21]):
                    squawk = idcode(payload)
                    msg_to_write = [full_message, time_hex, ts, localtime, downlink, squawk]
                    # Append to list of formatted messages for writing:
                    messages_to_write.append(msg_to_write)

                # Not interested - no squawk code:
                else:
                    pass

                # Update counter:
                decoder_message_count = decoder_message_count + 1

            # Messages decoded - Pipe list of decoded messages (in list form):
            try:
                decode_end.send(messages_to_write)
            except Exception as e:
                errorHandler('2b')

        # process termination control:
        except KeyboardInterrupt:
            run_decoder = False
            print("***************")
            time_now = str(datetime.utcnow())
            print("%s | Decoder message count: %d" %(time_now, decoder_message_count))
            print("%s | Decoder process terminated" %(time_now))
            continue    # Returns control to the top of the loop


"""Process that update filenames and write messages to file"""
def endpoint(endpoint_start):
    prev_fn = "dummy.txt"   # Dummy filename for initialisation
    run_endpoint = True
    endpoint_message_count = 0

    while run_endpoint:
        try:

            messages_to_write = []

            try:
                messages_to_write = endpoint_start.recv()   # receiving list of messages in list form here
            except Exception as e:
                errorHandler('3a')

            for message in messages_to_write:
                try:

                    # Routine to update filenames (using seconds):
                    # Extract timestamp and set it as temporary filename:
                    time_for_fn = message[2]    # float
                    # rounds it down using int (floor) and converts it to str:
                    filename = str(int(time_for_fn))
                    filename = filename+".txt"
                    
                    # if one second has passed, update filename:
                    if (filename!=prev_fn):
                        try:
                            prev_fn.close() # close the previous file
                        except:             # Expected error on first loop
                            pass
                        prev_fn = filename  # Update the old filename
                        file = open(prev_fn,"a")
                    
                    # Was a list, cast it into a string:
                    line = str(message)
                    # Remove '[' and ']' due to typecasting from list:
                    line_to_write = line[1::][:-1:]
                    # write to file with updated filename:
                    file.write("%s\n" %line_to_write)
                    # Update counter:
                    endpoint_message_count = endpoint_message_count + 1

                # Error - try to extract data for debugging:
                except Exception as e:
                    errorHandler('3b')

        except KeyboardInterrupt:
            run_endpoint = False
            print("***************")
            time_now = str(datetime.utcnow())
            print("%s | Endpoint message count: %d" %(time_now, endpoint_message_count))
            print("%s | Endpoint process terminated" %(time_now))
            continue    # Returns control to the top of the loop


"""Function to connect to hardcoded host, port"""
def connect():
    host = "169.254.210.120"
    port = 10003
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 10 seconds to return object before timeout:
            s.settimeout(10)
            s.connect((host, port))
            time_now = str(datetime.utcnow())
            print("%s | Server connected - %s:%s" %(time_now, host, port))
            print("%s | Collecting messages..." %(time_now))
            return s
        except socket.error as err:
            time_now = str(datetime.utcnow())
            print("%s | Socket connection error: %s. Reconnecting..." %(time_now, err))
            errorHandler('1a')
            time.sleep(3)


"""Main process that sets up architecture and collect data to pipe"""
if __name__ == '__main__':

    # Create pipes:
    decode_start, parent_end = multiprocessing.Pipe(False)
    endpoint_start, decode_end = multiprocessing.Pipe(False)

    # Create new child processes and give them pipe 'starts' and 'ends':
    decoding_process = multiprocessing.Process(target=decoder, args=(decode_start, decode_end))
    endpoint_process = multiprocessing.Process(target=endpoint, args=(endpoint_start,))

    # Start both child processes:
    decoding_process.start()
    endpoint_process.start()

    # Establish connection:
    time_now = str(datetime.utcnow())
    print("***************")
    print("%s | Script initiated" %(time_now))
    sock = connect()

    # Initialise 'slow-changing' variables:
    run_parent = True       # process control flag for key-board interrupt
    min_margin = 16384      # variable for 'margin check', stores minimum margin
    buffer = []             # buffer to store incoming data
    main_message_count = 0  # keep count the number of complete messages

    # Start receiving data:
    while run_parent:

        try:
            # Receive from socket:
            received = sock.recv(16384)

            # Check that we are receiving:
            if (len(received) == 0):
                errorHandler('1b')

            # Confirmed that we are receiving:
            else:

                # Check margin:
                margin = 16384 - len(received)

                # Check if margin is zero:
                if (margin == 0):
                    errorHandler('1c')
                    min_margin = margin

                # Even if not zero, update if there is a new minimum margin:
                elif (margin < min_margin):
                    min_margin = margin

            # Extends list to add newly received elements:
            buffer.extend(received)

            # Initialise/ empty lists with each loop, after sending:
            completed_msg_list = []
            completed_msg = []
            i = 0

            # process the buffer until the last divider <esc> 0x1a and reset buffer with remainder:
            while i < len(buffer):

                # Check if we are at a flag byte:
                if (buffer[i] != 0x1a):
                    # if we are not, append
                    completed_msg.append(buffer[i])
                    # try:
                        # completed_msg.append(buffer[i])
                    # except AttributeError as error:
                        # completed_msg = [completed_msg]
                        # completed_msg.extend(buffer[i])

                # we are at a flag byte:
                else:
                    # Check if we have reached the end of the buffer:
                    if (i == len(buffer) - 1):
                        # if so, append
                        completed_msg.append(0x1a)
                    # if we have not yet reached the end and the next byte is also a flag byte,
                    # the byte we are at is a 'stuffed' byte:
                    elif (buffer[i+1] == 0x1a):
                        # append, but skip the next byte:
                        completed_msg.append(0x1a)
                        i += 1
                    # if we have not yet reached the end and the next byte is not a flag byte,
                    # we have one complete message:
                    elif len(completed_msg) > 0:
                        completed_msg_list.append(completed_msg)
                        completed_msg = []
                        # Update counter:
                        main_message_count = main_message_count + 1

                i += 1

            # save the remainder for next reading cycle, if not empty:
            if len(completed_msg) > 0:
                remainder = []
                for i, m in enumerate(completed_msg):
                    if (m == 0x1a) and (i < len(completed_msg)-1):
                        # rewind 0x1a, except when it is at the last bit
                        remainder.extend([m, m])
                    else:
                        remainder.append(m)
                buffer = [0x1a] + remainder
            else:
                # Else empty, reset buffer
                buffer = []

            # Messages segmented - Pipe list of completed messages (in list form):
            try:
                parent_end.send(completed_msg_list)
            except Exception as e:
                errorHandler('1d')

        except KeyboardInterrupt:
            run_parent = False
            print("***************")
            # Print minimum buffer margin upon exit i.e. ideally we always want some margin
            time_now = str(datetime.utcnow())
            print("%s | Minimum buffer margin at socket: %d" %(time_now, min_margin))
            print("%s | Main message count: %d" %(time_now, main_message_count))
            print("%s | Main process terminated" %(time_now))
            print("***************")
            # Returns control to the top of the loop:
            continue

        except Exception as e:
            try:
                sock = connect()
            except Exception as e:
                errorHandler('1e')