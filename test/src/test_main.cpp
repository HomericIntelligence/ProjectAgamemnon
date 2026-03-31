#include "projectagamemnon/version.hpp"

#include <gtest/gtest.h>

namespace projectagamemnon::test {

TEST(VersionTest, ProjectNameIsCorrect) { EXPECT_EQ(kProjectName, "ProjectAgamemnon"); }

TEST(VersionTest, VersionIsSet) { EXPECT_FALSE(kVersion.empty()); }

}  // namespace projectagamemnon::test
