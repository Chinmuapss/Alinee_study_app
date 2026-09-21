class UserProfile {
  const UserProfile({required this.id, required this.fullName, required this.role});
  final String id, fullName, role;
  bool get isResponder => role == 'ADMIN' || role == 'RESPONDER';
  factory UserProfile.fromMap(Map<String, dynamic> data) => UserProfile(
    id: data['id'].toString(), fullName: data['full_name'] as String? ?? 'Community member',
    role: data['role'] as String? ?? 'REPORTER',
  );
}
