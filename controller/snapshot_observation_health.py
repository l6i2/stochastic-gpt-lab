"""Read the last positively identified Modern Standby sleep event, no power changes."""
import ctypes,xml.etree.ElementTree as ET
from ctypes import wintypes as W


def last_sleep_record_id():
    api=ctypes.WinDLL('wevtapi',use_last_error=True)
    api.EvtQuery.argtypes=[W.HANDLE,W.LPCWSTR,W.LPCWSTR,W.DWORD];api.EvtQuery.restype=W.HANDLE
    api.EvtNext.argtypes=[W.HANDLE,W.DWORD,ctypes.POINTER(W.HANDLE),W.DWORD,W.DWORD,ctypes.POINTER(W.DWORD)];api.EvtNext.restype=W.BOOL
    api.EvtRender.argtypes=[W.HANDLE,W.HANDLE,W.DWORD,W.DWORD,W.LPVOID,ctypes.POINTER(W.DWORD),ctypes.POINTER(W.DWORD)];api.EvtRender.restype=W.BOOL
    api.EvtClose.argtypes=[W.HANDLE];api.EvtClose.restype=W.BOOL
    query="*[System[Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=507] and EventData[Data[@Name='SleepEntered']='true']]"
    handle=api.EvtQuery(None,'System',query,0x201)
    if not handle:raise OSError(ctypes.get_last_error(),'SLEEP_EVENT_QUERY_FAILED')
    event=W.HANDLE();count=W.DWORD()
    try:
        if not api.EvtNext(handle,1,ctypes.byref(event),1000,0,ctypes.byref(count)):
            error=ctypes.get_last_error()
            if error==259:return 0
            raise OSError(error,'SLEEP_EVENT_READ_FAILED')
        needed=W.DWORD();properties=W.DWORD();api.EvtRender(None,event,1,0,None,ctypes.byref(needed),ctypes.byref(properties))
        if not needed.value or needed.value>65536:raise RuntimeError('EVENT_BUFFER_UNAVAILABLE_OR_EXCESSIVE')
        buffer=ctypes.create_unicode_buffer((needed.value+1)//2)
        if not api.EvtRender(None,event,1,needed.value,buffer,ctypes.byref(needed),ctypes.byref(properties)):raise OSError(ctypes.get_last_error(),'SLEEP_EVENT_RENDER_FAILED')
        root=ET.fromstring(buffer.value);ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
        return int(root.find('e:System/e:EventRecordID',ns).text)
    finally:
        if event:api.EvtClose(event)
        api.EvtClose(handle)
