import win32service
import win32serviceutil
import win32event
import time
import os
import glob
import struct
import hashlib
from asn1crypto.core import Sequence, OctetString, UTF8String

# Folders and device names
WATCH_FOLDER = r"C:\watched"
PROCESSED_FOLDER = os.path.join(WATCH_FOLDER, "processed")
SERIAL_PORT = r"\\.\Global\attestation_channel" 

# ASN.1 FileContainer definition: a SEQUENCE with two fields.
class FileContainer(Sequence):
    _fields = [
        ('filename', UTF8String),
        ('data', OctetString)
    ]

def create_file_container(filename, data):
    """
    Build and return a DER-encoded FileContainer containing the filename and file data.
    """
    container = FileContainer({
        'filename': filename,
        'data': data
    })
    return container.dump()

class XPFileMonitorService(win32serviceutil.ServiceFramework):
    _svc_name_ = "XPFileMonitorService"
    _svc_display_name_ = "XP File Monitor Service"
    _svc_description_ = ("Monitors a folder for new files and sends each file's name and data "
                         "to the Linux control server over the virtio-serial channel using a DER-encoded container.")

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.processed_files_path = r"C:\list_of_signed_results.txt"

    def load_processed_files(self):
        """Load the set of processed file hashes from disk."""
        processed_files = set()
        try:
            if os.path.exists(self.processed_files_path):
                with open(self.processed_files_path, "r") as f:
                    processed_files = set(line.strip() for line in f)
        except Exception as e:
            with open(r"C:\XPFileMonitorService.log", "a") as log:
                log.write("Error loading processed files: {}\n".format(e))
        return processed_files

    def save_processed_files(self, processed_files):
        """Save the set of processed file hashes to disk."""
        try:
            with open(self.processed_files_path, "w") as f:
                for file_hash in processed_files:
                    f.write("{}\n".format(file_hash))
        except Exception as e:
            with open(r"C:\XPFileMonitorService.log", "a") as log:
                log.write("Error saving processed files: {}\n".format(e))

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        # Ensure the processed folder exists.
        if not os.path.exists(PROCESSED_FOLDER):
            os.makedirs(PROCESSED_FOLDER)
        self.main()

    def main(self):
        try:
            # Open the virtio-serial port in binary read/write mode.
            serial_port = open(SERIAL_PORT, "wb+", buffering=0)
        except Exception as e:
            with open(r"C:\XPFileMonitorService.log", "a") as log:
                log.write("Failed to open serial port {}: {}\n".format(SERIAL_PORT, e))
            return

        # Load the set of previously processed files
        processed_files = self.load_processed_files()

        while self.running:
            try:
                # Look for files in the watch folder (ignore subdirectories).
                files = glob.glob(os.path.join(WATCH_FOLDER, "*"))
                new_files = []
                
                # Filter for unique files we haven't processed before
                for file_path in files:
                    if os.path.isfile(file_path):
                        with open(file_path, "rb") as f:
                            file_hash = hashlib.sha256(f.read()).hexdigest()
                        if file_hash not in processed_files:
                            new_files.append((file_path, file_hash))

                if new_files:
                    # Wait 5 seconds before processing the files
                    time.sleep(5)
                    
                    for file_path, file_hash in new_files:
                        filename = os.path.basename(file_path)
                        try:
                            with open(file_path, "rb") as f:
                                file_data = f.read()

                            # Create the DER-encoded file container.
                            container_der = create_file_container(filename, file_data)
                            container_length = len(container_der)

                            # Build the message: 4-byte length prefix (big-endian) + DER data.
                            message = struct.pack("!I", container_length) + container_der

                            # Write the message to the virtio-serial port.
                            serial_port.write(message)
                            serial_port.flush()

                            # Log the sent file.
                            with open(r"C:\XPFileMonitorService.log", "a") as log:
                                log.write("Sent file: {} ({} bytes)\n".format(filename, len(file_data)))

                            # Move the processed file.
                            dest_path = os.path.join(PROCESSED_FOLDER, filename)
                            os.rename(file_path, dest_path)
                            
                            # Add to processed files set and save
                            processed_files.add(file_hash)
                            self.save_processed_files(processed_files)
                            
                        except Exception as e:
                            with open(r"C:\XPFileMonitorService.log", "a") as log:
                                log.write("Error processing file {}: {}\n".format(filename, e))

                time.sleep(30)
                
            except Exception as e:
                with open(r"C:\XPFileMonitorService.log", "a") as log:
                    log.write("Error in main loop: {}\n".format(e))
                time.sleep(5)
                
        serial_port.close()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(XPFileMonitorService)
