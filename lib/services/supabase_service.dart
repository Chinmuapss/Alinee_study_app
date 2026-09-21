import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class SupabaseService {
  static SupabaseClient get client => Supabase.instance.client;
  static Future<void> initialize() async {
    await dotenv.load(fileName: '.env');
    final url = dotenv.env['SUPABASE_URL'];
    final key = dotenv.env['SUPABASE_ANON_KEY'];
    if (url == null || key == null || url.contains('your-project')) {
      throw StateError('Supabase is not configured. Copy .env.example to .env and add your project URL and anon key.');
    }
    await Supabase.initialize(url: url, anonKey: key);
  }
}
