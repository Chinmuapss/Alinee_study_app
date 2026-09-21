import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/user_profile.dart';
import 'supabase_service.dart';

class AuthService {
  final _client = SupabaseService.client;
  Stream<AuthState> get authChanges => _client.auth.onAuthStateChange;
  User? get currentUser => _client.auth.currentUser;
  Future<void> signIn(String email, String password) => _client.auth.signInWithPassword(email: email, password: password);
  Future<void> signUp(String name, String email, String password) async {
    await _client.auth.signUp(email: email, password: password, data: {'full_name': name});
  }
  Future<void> signOut() => _client.auth.signOut();
  Future<UserProfile> profile() async => UserProfile.fromMap(await _client.from('profiles').select().eq('id', currentUser!.id).single());
}
