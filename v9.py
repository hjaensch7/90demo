import json
from urllib.parse import parse_qs, quote, unquote

CRIT_ERROR_STRING = quote("{\"response_body\":\"\",\"http_response_code\":543,\"internal_error\":true,\"error_message\":\"can't even serialize what we're working with!\"}") + "\n"


def serialize_response(response_code, body, *, internal_error=None):
    try:
        resp = {
            "response_body": str(body),
            "http_response_code": int(response_code)
        }
        if internal_error is not None:
            resp["error_message"] = str(internal_error)

        return str.encode(quote(json.dumps(resp)) + "\n")
    except Exception:
        return str.encode(CRIT_ERROR_STRING)


class V9Component(object):
    def __init__(self, in_file, out_file):
        self.in_file = in_file
        self.out_file = out_file
        self.functions = {}

    def register_operation(self, name, function):
        self.functions[name] = function

    def _get_response(self, line):
        try:
            deserialized_line = json.loads(unquote(line.decode("utf-8")))
        except Exception as e:
            # 543 = internal error
            # (This means the node has messed up serializing the line)
            return serialize_response(543, "", internal_error="Invalid line " + str(line) + " exception " + repr(e))

        try:
            function = deserialized_line["called_function"]
            http_method = deserialized_line["http_method"]
            path = deserialized_line["path"]
            request_arguments = parse_qs(deserialized_line["request_arguments"])
            request_body = deserialized_line["request_body"]

            if function not in self.functions:
                return serialize_response(404, "Function not found!")

            try:
                (response_code, response_body) = self.functions[function](http_method, path, request_arguments, request_body)
            except Exception as e:
                return serialize_response(500, "User function failed " + repr(e))

            return serialize_response(response_code, response_body)
        except KeyError:
            # 543 = internal error
            # (This means the node has messed up serializing the line)
            return serialize_response(543, "", internal_error="Invalid request " + deserialized_line)

    def loop(self):
        try:
            with open(self.out_file, 'bw') as out_file:
                with open(self.in_file, 'br') as in_file:
                    try:
                        while True:
                            line = read_line(in_file)
                            # This means no one is writing to the pipe anymore
                            if line == "":
                                return

                            resp = self._get_response(line)
                            out_file.write(resp)
                            out_file.flush()
                    except Exception as e:
                        out_file.write(serialize_response(543, "", internal_error=repr(e)))
                        out_file.flush()
        except Exception as e:
            out_file.write(serialize_response(543, "", internal_error="Unexpected file handling error " + repr(e)))
            out_file.flush()
            raise


def read_line(f):
    res = bytes()
    while True:
        res += f.read(1)
        if res[-1] == b'\n'[-1]:
            return res


