import os

from CSIKit.csi import CSIData
from CSIKit.csi.frames import ESP32CSIFrame
from CSIKit.reader import Reader
from CSIKit.util import csitools, constants

ESP32_HEADER = ["type", "role", "mac", "rssi", "rate", "sig_mode", "mcs", "bandwidth", "smoothing", "not_sounding",
                "aggregation", "stbc", "fec_coding", "sgi", "noise_floor", "ampdu_cnt", "channel", "secondary_channel",
                "local_timestamp", "ant", "sig_len", "rx_state", "real_time_set", "real_timestamp", "len", "CSI_DATA"]

HEADER_NAME_MAPPINGS = {
    "ESP32": ESP32_HEADER
}

HEADER_FRAMES = {
    "ESP32": ESP32CSIFrame
}

BACKEND_MAPPING = {
    "ESP32": "ESP32 CSI Tool"
}

class CSVBeamformReader(Reader):

    def __init__(self):
        pass

    @staticmethod
    def can_read(path: str) -> bool:
        if os.path.exists(path) and os.path.splitext(path)[1] == ".csv":
            try:
                data = open(path)

                first_line = data.readline()[:-1]
                second_line = data.readline()[:-1]

                first_split = first_line.split(",")
                second_split = second_line.split(",")

                # If they are not the same length then the
                # CSV is malformed or contains a separate header line.
                if len(first_split) == len(second_split):
                    # If we have observe a supported header format.
                    # TODO: Add functionality to add your own headers.
                    return first_split in HEADER_NAME_MAPPINGS.values()
            except UnicodeDecodeError as _:
                return False

        return False

    def read_file(self, path: str, scaled: bool = False, remove_unusable_subcarriers: bool = True) -> CSIData:

        # if scaled:
        #     print("Scaling not yet supported in CSV formats.")

        self.filename = os.path.basename(path)
        if not os.path.exists(path):
            raise Exception("File not found: {}".format(path))

        data = open(path, "r")

        ret_data = CSIData(self.filename, "", "CSV Format")

        header_line = data.readline()[:-1].split(",")

        # TODO: Add support for adding custom headers.
        if header_line not in HEADER_NAME_MAPPINGS.values():
            print("Unsupported CSV format.")
            exit(1)

        header_name = None
        for key, val in HEADER_NAME_MAPPINGS.items():
            if val == header_line:
                header_name = key
                break

        if not header_name:
            print("Unable to find hardware name for format.")
            exit(1)

        ret_data.set_chipset(header_name)
        ret_data.set_backend(BACKEND_MAPPING[header_name])

        header_frame = HEADER_FRAMES[header_name]

        while True:
            data_line = data.readline().split(",")
            if not data_line or len(data_line) != len(header_line):
                break

            new_frame = header_frame(data_line)

            if ret_data.bandwidth == 0:
                ret_data.bandwidth = new_frame.bandwidth

            if scaled:
                new_frame.csi_matrix = csitools.scale_csi_frame(new_frame.csi_matrix, new_frame.rssi)

            # no_subcarriers = new_frame.csi_matrix.shape[0]

            # if remove_unusable_subcarriers and header_name == "ESP32":
            #     new_frame.csi_matrix = new_frame.csi_matrix[[x for x in range(no_subcarriers) if x not in constants.ESP32_20MHZ_UNUSABLE]]
            # elif remove_unusable_subcarriers:
            #     print("Unsupported header format for null/pilot/guard subcarrier removal.")

            ret_data.push_frame(new_frame)
            #TODO: Normalise the timestamp retrieval.
            ret_data.timestamps.append(float(new_frame.real_timestamp))

        return ret_data