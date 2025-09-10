class DeviceStatus():
    #   _OFF          = b'\x00'
    #   _BOOTING      = b'\x01'  commentout numbers used by BOSS PIC only
    _IDLE         = b'\x02'
    _BUSY         = b'\x03'
    _SMF_COPY_REQ = b'\x04'
    _COPYING      = b'\x05'
    _FINISHED     = b'\x06'

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DeviceStatus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.is_executing_mission = False  # type: bool
        self.is_allowed_to_copy_smf = False  # type: bool
        self.status = self.__class__._IDLE  # type: bytes
        self._initialized = True

    def request_smf(self):
        self.status = self.__class__._SMF_COPY_REQ
    
    def is_can_use_smf(self):
        return self.is_allowed_to_copy_smf

    def start_use_smf(self):
        self.status = self.__class__._COPYING
    
    def end_use_smf(self):
        self.is_allowed_to_copy_smf = False
        self.status = self.__class__._IDLE
