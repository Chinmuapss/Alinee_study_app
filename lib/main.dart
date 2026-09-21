import 'package:flutter/material.dart';
import 'services/auth_service.dart';
import 'services/supabase_service.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'utils/constants.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try { await SupabaseService.initialize(); runApp(const IBantayApp()); }
  catch (error) { runApp(ConfigurationErrorApp(error.toString())); }
}

class IBantayApp extends StatelessWidget {
  const IBantayApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(title: appName, debugShowCheckedModeBanner: false, theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: safetyNavy, brightness: Brightness.light), useMaterial3: true), home: const AuthGate());
}
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});
  @override Widget build(BuildContext context) => StreamBuilder(stream: AuthService().authChanges, builder: (_, __) => AuthService().currentUser == null ? const LoginScreen() : const HomeScreen());
}
class ConfigurationErrorApp extends StatelessWidget {
  const ConfigurationErrorApp(this.message, {super.key}); final String message;
  @override Widget build(BuildContext context) => MaterialApp(home: Scaffold(body: Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('iBantay needs configuration.\n\n$message', textAlign: TextAlign.center)))));
}
