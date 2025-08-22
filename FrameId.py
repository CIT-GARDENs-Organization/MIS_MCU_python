class FrameId():
    #Receives
    UPLINK_COMMAND = 0x0
    _UPLINK_COMMAND_CONTENT_LENGTH = 9
    STATUS_CHECK = 0x1
    _STATUS_CHECK_CONTENT_LENGTH = 0
    IS_SMF_AVAILABLE = 0x2
    _IS_SMF_AVAILABLE_CONTENT_LENGTH = 1
    frame_ids_content_length = {UPLINK_COMMAND:     _UPLINK_COMMAND_CONTENT_LENGTH, 
                                STATUS_CHECK:       _STATUS_CHECK_CONTENT_LENGTH, 
                                IS_SMF_AVAILABLE:  _IS_SMF_AVAILABLE_CONTENT_LENGTH, 
                                }

    #Transmits
    MIS_MCU_STATUS = 0x3
    ACK = 0xF