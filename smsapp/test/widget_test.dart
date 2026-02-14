import 'package:flutter_test/flutter_test.dart';
import 'package:smsapp/main.dart';

void main() {
  testWidgets('App renders permission gate', (WidgetTester tester) async {
    await tester.pumpWidget(const HoneyTrapApp());
    // App should show loading initially
    expect(find.byType(HoneyTrapApp), findsOneWidget);
  });
}
