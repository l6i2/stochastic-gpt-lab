"""Read-only RFC8915 measurement. No OS clock adjustment or broker mapping."""
import hashlib
import secrets
import select
import socket
import ssl
import struct
import time
import uuid

EPOCH=2208988800


def receive_clock_sample():
    """Bracket the local wall read, not packet arrival or broker generation."""
    if __import__('sys').platform!='win32':
        a=time.perf_counter_ns();host=time.time_ns();b=time.perf_counter_ns()
        return host,None,dict(perf_counter_ns_interval=[a,b],scope='LOCAL_WALL_READ_NOT_PACKET_ARRIVAL')
    import ctypes
    api=ctypes.windll.kernel32;api.GetTickCount64.restype=ctypes.c_ulonglong
    frequency=ctypes.c_longlong();a=ctypes.c_longlong();b=ctypes.c_longlong()
    if not api.QueryPerformanceFrequency(ctypes.byref(frequency)) or frequency.value<=0:raise ValueError('QPC_FREQUENCY_UNAVAILABLE')
    uptime_a=api.GetTickCount64()
    if not api.QueryPerformanceCounter(ctypes.byref(a)):raise ValueError('QPC_UNAVAILABLE')
    host=time.time_ns()
    if not api.QueryPerformanceCounter(ctypes.byref(b)):raise ValueError('QPC_UNAVAILABLE')
    uptime_b=api.GetTickCount64()
    return host,[uptime_a,uptime_b],dict(qpc_ticks_interval=[a.value,b.value],qpc_frequency_hz=frequency.value,
        scope='LOCAL_WALL_READ_NOT_PACKET_ARRIVAL',uptime_resolution_bound='NOT_CALIBRATED',
        qpc_absolute_utc_accuracy='NOT_IMPLIED_BY_RESOLUTION')


def offset_bounds(t1,t2,t3,t4,error):
    if error<0 or t3<t2 or t4<t1:raise ValueError('INVALID_TIME_MODEL')
    lower,upper=t3-t4-error,t2-t1+error
    if lower>upper:raise ValueError('OFFSET_INTERVAL_INCONSISTENT')
    return [lower,upper]


def stamp(ns):
    seconds,nanos=divmod(ns,1000000000)
    return struct.pack('!II',seconds+EPOCH,nanos*2**32//1000000000)


def unstamp(value):
    seconds,fraction=struct.unpack('!II',value)
    return (seconds-EPOCH)*1000000000+fraction*1000000000//2**32


def extension(kind,body):
    body+=b'\0'*(-len(body)%4)
    return struct.pack('!HH',kind,len(body)+4)+body


def fields(packet,offset=48):
    while offset<len(packet):
        if offset+4>len(packet):raise ValueError('SHORT_EXTENSION')
        kind,size=struct.unpack_from('!HH',packet,offset)
        if size<4 or size%4 or offset+size>len(packet):raise ValueError('INVALID_EXTENSION_LENGTH')
        yield kind,packet[offset+4:offset+size],offset
        offset+=size


def verify_response(packet,key,uid,origin):
    from cryptography.hazmat.primitives.ciphers.aead import AESSIV
    if len(packet)<48 or packet[0]&7!=4 or (packet[0]>>3)&7!=4 or packet[0]>>6==3 or not 1<=packet[1]<=15:
        raise ValueError('INVALID_NTP_STATE')
    if packet[24:32]!=origin:raise ValueError('ORIGIN_MISMATCH')
    seen_uid=False;authenticated=False
    for kind,body,offset in fields(packet):
        if authenticated:raise ValueError('UNAUTHENTICATED_TRAILING_FIELDS')
        if kind==0x104:
            if seen_uid or body!=uid:raise ValueError('UID_MISMATCH_OR_DUPLICATE')
            seen_uid=True
        elif kind==0x404:
            if not seen_uid or len(body)<4:raise ValueError('AUTHENTICATOR_STRUCTURE')
            nl,cl=struct.unpack_from('!HH',body)
            padded=(nl+3)//4*4
            if nl<16 or cl<16 or 4+padded+cl>len(body):raise ValueError('AUTHENTICATOR_LENGTH')
            plaintext=AESSIV(key).decrypt(body[4+padded:4+padded+cl],[packet[:offset],body[4:4+nl]])
            # Encrypted fields must themselves have valid framing.
            for k,b,o in fields(plaintext,0):
                if k!=0x204:raise ValueError('UNEXPECTED_ENCRYPTED_FIELD')
            authenticated=True
        elif kind in (0x204,0x304):raise ValueError('UNENCRYPTED_SERVER_COOKIE')
    if not authenticated:raise ValueError('AUTHENTICATOR_MISSING')
    t2,t3=unstamp(packet[32:40]),unstamp(packet[40:48])
    if t3<t2:raise ValueError('SERVER_TIME_ORDER')
    return t2,t3


def measure(host,cafile):
    from OpenSSL import SSL,crypto
    from cryptography import x509
    from cryptography.hazmat.primitives.ciphers.aead import AESSIV
    context=SSL.Context(SSL.TLS_CLIENT_METHOD)
    context.set_min_proto_version(SSL.TLS1_3_VERSION)
    context.load_verify_locations(str(cafile))
    context.set_verify(SSL.VERIFY_PEER,lambda c,cert,errno,depth,ok:ok)
    context.set_alpn_protos([b'ntske/1'])
    raw=socket.create_connection((host,4460),timeout=4);raw.setblocking(False)
    connection=SSL.Connection(context,raw);connection.set_connect_state();connection.set_tlsext_host_name(host.encode())
    deadline=time.monotonic()+8
    def io(method,*args):
        while True:
            if time.monotonic()>deadline:raise TimeoutError('NTS_KE_DEADLINE')
            try:return method(*args)
            except SSL.WantReadError:select.select([raw],[],[],max(0,deadline-time.monotonic()))
            except SSL.WantWriteError:select.select([],[raw],[],max(0,deadline-time.monotonic()))
    try:
        io(connection.do_handshake)
        if connection.get_alpn_proto_negotiated()!=b'ntske/1':raise ValueError('NTS_ALPN_REQUIRED')
        cert=connection.get_peer_certificate().to_cryptography()
        from cryptography.x509.verification import PolicyBuilder,Store,DNSName
        roots=x509.load_pem_x509_certificates(__import__('pathlib').Path(cafile).read_bytes())
        PolicyBuilder().store(Store(roots)).build_server_verifier(DNSName(host)).verify(
            cert,[c.to_cryptography() for c in connection.get_peer_cert_chain()[1:]])
        request=bytes.fromhex('80010002000080040002000f80000000')
        sent=0
        while sent<len(request):sent+=io(connection.send,request[sent:])
        def read(size):
            value=b''
            while len(value)<size:
                part=io(connection.recv,size-len(value))
                if not part:raise ValueError('TRUNCATED_NTS_KE')
                value+=part
            return value
        records={};cookies=[];total=0;ntp_host=host;port=123
        while True:
            word,size=struct.unpack('!HH',read(4));total+=size+4
            if total>65536:raise ValueError('NTS_KE_SIZE_LIMIT')
            body=read(size);kind=word&0x7fff
            if kind==0:
                if size or not word&0x8000:raise ValueError('INVALID_END_RECORD')
                break
            if kind in (2,3):raise ValueError('NTS_KE_SERVER_ERROR')
            if kind==5:cookies.append(body)
            elif kind in (1,4,6,7):
                if kind in records:raise ValueError('DUPLICATE_NTS_KE_RECORD')
                records[kind]=body
            elif word&0x8000:raise ValueError('UNKNOWN_CRITICAL_RECORD')
        if records.get(1)!=b'\0\0' or records.get(4)!=b'\0\x0f' or not cookies:raise ValueError('NTS_NEGOTIATION_INCOMPLETE')
        if 6 in records:ntp_host=records[6].decode('ascii')
        if 7 in records:
            if len(records[7])!=2:raise ValueError('INVALID_NTP_PORT')
            port=struct.unpack('!H',records[7])[0]
        if port!=123:raise ValueError('UNEXPECTED_NTP_PORT')
        keys=[connection.export_keying_material(b'EXPORTER-network-time-security',32,struct.pack('!HHB',0,15,d)) for d in (0,1)]
        cert_sha=hashlib.sha256(crypto.dump_certificate(crypto.FILETYPE_ASN1,connection.get_peer_certificate())).hexdigest()
    finally:
        connection.close();raw.close()
    uid=secrets.token_bytes(32);nonce=secrets.token_bytes(16)
    t1=time.time_ns();m1=time.perf_counter_ns()
    header=b'\x23'+bytes(39)+stamp(t1)
    aad=header+extension(0x104,uid)+extension(0x204,cookies[0])+extension(0x304,bytes(len(cookies[0])))
    encrypted=AESSIV(keys[0]).encrypt(b'',[aad,nonce])
    request=aad+extension(0x404,struct.pack('!HH',len(nonce),len(encrypted))+nonce+encrypted)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
        client.settimeout(4);client.connect((ntp_host,port));client.send(request);packet=client.recv(8192)
    m4=time.perf_counter_ns();t4,kernel_interval,clock_observation=receive_clock_sample();m4_after=time.perf_counter_ns()
    t2,t3=verify_response(packet,keys[1],uid,request[40:48])
    # Keys/cookies are ephemeral and never serialized or published.
    delay=struct.unpack('!i',packet[4:8])[0]*1000000000//65536
    dispersion=struct.unpack('!I',packet[8:12])[0]*1000000000//65536
    precision=struct.unpack('!b',packet[3:4])[0]
    precision_ns=max(1,__import__('math').ceil(2.0**precision*1000000000))
    advertised_error=max(0,delay)//2+dispersion+precision_ns+1
    lower,upper=offset_bounds(t1,t2,t3,t4,advertised_error)
    return dict(capture_id=uuid.uuid4().hex,origin=host,protocol='RFC8915_NTS_AEAD15_TLS13',
        authentication='TLS_CHAIN_HOSTNAME_ALPN_EXPORTER_AEAD_UID_ORIGIN_VERIFIED',peer_certificate_sha256=cert_sha,
        server_receive_utc_ns=t2,server_transmit_utc_ns=t3,host_send_ns=t1,host_receive_ns=t4,
        rtt_monotonic_ns=m4_after-m1,rtt_local_read_interval_ns=[m4-m1,m4_after-m1],
        rtt_scope='QUERY_ELAPSED_INCLUDES_LOCAL_PROCESSING_NOT_PURE_NETWORK_DELAY',server_processing_ns=t3-t2,
        stratum=packet[1],leap_indicator=packet[0]>>6,root_delay_ns=delay,
        root_dispersion_ns=dispersion,precision_log2_seconds=precision,
        offset_server_minus_host_ns=[lower,upper],server_advertised_error_ns=advertised_error,
        utc_receive_interval_model_ns=[t4+lower,t4+upper],
        receive_kernel_uptime_ms_interval=kernel_interval,
        receive_clock_observation=clock_observation,
        host_elapsed_minus_monotonic_ns=(t4-t1)-(m4-m1),
        host_elapsed_minus_monotonic_interval_ns=[(t4-t1)-(m4_after-m1),(t4-t1)-(m4-m1)],
        uncertainty_scope='Conditional on server advertised error and local clock stability; not a metrological absolute bound',
        response_sha256=hashlib.sha256(packet).hexdigest(),unique_id_sha256=hashlib.sha256(uid).hexdigest(),
        broker_mapping_authorized=False,clock_adjusted=False)
