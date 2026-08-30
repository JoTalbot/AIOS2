from security.audit import AuditEvent, allow


def test_audit_event():
    event = AuditEvent('runtime', 'read', 'state', 'ok')
    assert event.result == 'ok'


def test_permission_check():
    assert allow('execute', {'execute'})
    assert not allow('write', {'read'})
