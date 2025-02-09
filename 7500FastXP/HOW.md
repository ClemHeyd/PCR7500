# Windows XP VM for 7500 Fast PCR System

This VM runs Windows XP SP3 with Windows SteadyState to provide a locked-down environment for running the ThermoFisher Scientific 7500 Fast PCR System software.

This was necessary, because the PCR system uses proprietary USB drivers and protocol.

There was no way of running the PCR system software without running it Windows XP.

We've locked down the environment such that only results produced by the PCR Software can be signed.

The signing of scientific results is done by a custom Python service that runs outside of the VM.

The Windows XP VM communicates with the service via a virtio-serial device.

## Specifications

### Base System
- Windows XP Professional SP3 (Pre-Activated)
- Python 3.4.4 (Last Supported Version)

### Security & Restrictions
- Windows SteadyState provides disk protection and user restrictions
- Limits user to only running the 7500 Fast PCR software
- Registry locked down to prevent modifications
- All system changes are discarded on reboot
    
### Technical Details
- Base image from: https://archive.org/details/XPProSP3ActivatedIE8WMP11
- SteadyState from: https://archive.org/details/SteadyState
- Custom Python 3.4.4 `win32service` to monitor for new results, copy them to the host
- Python 3.12 script running on the host to sign the results
- Communication via the virtio-serial device (virtualized serial port)

## Steps To Reproduce

1. Install QEMU/KVM and virt-manager
2. Create a new VM with the following parameters:
    - Arch: i686
    - Memory: 2048MB
    - Disk: 4GB
    - Network: virtio-net
    - Serial: virtio-serial
    - USB Passthrough: ID 0c2b:0300 Neuron, Inc. Hamamatsu C9254-01
3. Install the Windows XP SP3 image from the archive.org link
4. Install the SteadyState image from the archive.org link
5. Install Python 3.4.4 from the official source
6. Install the `win32service` and `asn1crypto` packages from the official source
7. Install the Python 3.4.4 service from the `service.py` file
8. Install the 7500 Fast PCR System Software (Can't Offer It Here, Obtained Under Service Agreement)
9. Use SteadyState to lock down the system and restrict the user to only running the 7500 Fast PCR System Software