import 'package:flutter/material.dart';
import '../dashboard/dashboard_screen.dart';
import '../models/user_profile.dart';
import '../services/auth_service.dart';
import '../utils/constants.dart';
import '../widgets/emergency_button.dart';
import '../widgets/incident_card.dart';
import 'profile_screen.dart';
import 'report_history_screen.dart';
import 'report_screen.dart';
class HomeScreen extends StatefulWidget { const HomeScreen({super.key}); @override State<HomeScreen> createState()=>_HomeScreenState(); }
class _HomeScreenState extends State<HomeScreen> { late Future<UserProfile> profile; @override void initState(){super.initState();profile=AuthService().profile();}
  void report(String type,{bool emergency=false})=>Navigator.push(context,MaterialPageRoute(builder:(_)=>ReportScreen(incidentType:type,isEmergency:emergency)));
  @override Widget build(BuildContext context)=>FutureBuilder<UserProfile>(future:profile,builder:(context,snapshot){if(snapshot.hasError)return const Scaffold(body:Center(child:Text('Unable to load your profile. Please refresh or sign in again.')));if(!snapshot.hasData)return const Scaffold(body:Center(child:CircularProgressIndicator()));final user=snapshot.data!;return Scaffold(appBar:AppBar(title:const Text(appName),actions:[IconButton(onPressed:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const ProfileScreen())),icon:const Icon(Icons.person_outline))]),drawer:Drawer(child:ListView(children:[DrawerHeader(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Icon(Icons.shield,color:Colors.white,size:38),Text(appName,style:const TextStyle(color:Colors.white,fontSize:25,fontWeight:FontWeight.bold))]),decoration:const BoxDecoration(color:safetyNavy)),ListTile(leading:const Icon(Icons.history),title:const Text('My Reports'),onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const ReportHistoryScreen()))),if(user.isResponder) ListTile(leading:const Icon(Icons.dashboard),title:const Text('Responder Dashboard'),onTap:()=>Navigator.push(context,MaterialPageRoute(builder:(_)=>const DashboardScreen()))),ListTile(leading:const Icon(Icons.logout),title:const Text('Logout'),onTap:()=>AuthService().signOut())]),body:SafeArea(child:Padding(padding:const EdgeInsets.all(18),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('Welcome, ${user.fullName}',style:Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight:FontWeight.bold)),const Text('Select an incident type to begin a report.'),const SizedBox(height:18),EmergencyButton(onPressed:()=>report('Other Emergency',emergency:true)),const SizedBox(height:20),Text('Report an incident',style:Theme.of(context).textTheme.titleLarge),const SizedBox(height:8),Expanded(child:GridView.count(crossAxisCount:MediaQuery.sizeOf(context).width>600?3:2,childAspectRatio:2.2,children:incidentTypes.map((e)=>IncidentCard(type:e,onTap:()=>report(e.name))).toList()))])));}); }
}
